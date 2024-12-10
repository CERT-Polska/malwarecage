import json
from uuid import UUID

from flask import g, request
from werkzeug.exceptions import BadRequest, Forbidden, MethodNotAllowed, NotFound

from mwdb.core.capabilities import Capabilities
from mwdb.core.config import app_config
from mwdb.core.deprecated import DeprecatedFeature, uses_deprecated_api
from mwdb.core.plugins import hooks
from mwdb.core.search import QueryBaseException, build_query
from mwdb.core.service import Resource
from mwdb.model import AttributeDefinition, Object, db
from mwdb.model.tag import Tag
from mwdb.schema.object import (
    ObjectCountRequestSchema,
    ObjectCountResponseSchema,
    ObjectItemAndRelationsResponseSchema,
    ObjectItemRequestSchema,
    ObjectItemResponseSchema,
    ObjectListRequestSchema,
    ObjectListResponseSchema,
)

from . import (
    get_shares_for_upload,
    get_type_from_str,
    load_schema,
    logger,
    requires_authorization,
    requires_capabilities,
)


class ObjectUploader:
    """
    Mixin adding common object upload capabilities to resource

    Merge it with ObjectsResource during retirement of ObjectResource
    deprecated upload methods
    """

    ObjectType = None
    ItemResponseSchema = None

    def on_created(self, object, params):
        if app_config.mwdb.enable_karton and not object.is_analyzed():
            object.spawn_analysis(arguments=params.get("karton_arguments", {}))
        hooks.on_created_object(object)
        tags = params.get("tags")
        for tag in tags:
            db_tag = Tag(tag=tag["tag"], object_id=object.id)
            hooks.on_created_tag(object, db_tag)

    def on_reuploaded(self, object, params):
        hooks.on_reuploaded_object(object)

    def _create_object(
        self, spec, parent, share_with, attributes, analysis_id, tags, share_3rd_party
    ):
        # To be implemented by specialized uploaders (e.g. FileUploader)
        raise NotImplementedError

    def create_object(self, params):
        params = dict(params)

        # Validate parent object
        if params["parent"] is not None:
            if not g.auth_user.has_rights(Capabilities.adding_parents):
                raise Forbidden("You are not permitted to link with parent")

            parent_object = Object.access(params["parent"])

            if parent_object is None:
                raise NotFound("Parent object not found")
        else:
            parent_object = None

        # Validate metakeys and Karton assignment
        analysis_id = params.get("karton_id")

        if params["metakeys"]:
            uses_deprecated_api(DeprecatedFeature.legacy_metakeys_upload_option)
            # If 'metakeys' are defined: keep legacy behavior
            if "attributes" in params and params["attributes"]:
                raise BadRequest("'attributes' and 'metakeys' options can't be mixed")

            attributes = params["metakeys"]
            for attribute in params["metakeys"]:
                key = attribute["key"]
                if key == "karton":
                    if analysis_id is not None:
                        raise BadRequest(
                            "You can't provide more than one Karton analysis identifier"
                        )
                    try:
                        analysis_id = UUID(attribute["value"])
                    except (ValueError, AttributeError):
                        raise BadRequest("'karton' attribute accepts only UUID values")
                elif not AttributeDefinition.query_for_set(key).first():
                    raise NotFound(
                        f"Attribute '{key}' not defined or insufficient "
                        "permissions to set that one"
                    )
        else:
            # If not, rely on 'attributes'
            attributes = params["attributes"]
            for attribute in params["attributes"]:
                key = attribute["key"]
                if not AttributeDefinition.query_for_set(key).first():
                    raise NotFound(
                        f"Attribute '{key}' not defined or insufficient "
                        "permissions to set that one"
                    )

        if analysis_id is not None:
            if not g.auth_user.has_rights(Capabilities.karton_assign):
                raise Forbidden(
                    "You are not permitted to assign Karton analysis to object"
                )

        # Validate upload_as argument
        share_with = get_shares_for_upload(params["upload_as"])

        # Tags argument
        tags = params.get("tags")

        share_3rd_party = params.get("share_3rd_party", True)

        item, is_new = self._create_object(
            params,
            parent_object,
            share_with,
            attributes,
            analysis_id,
            tags,
            share_3rd_party,
        )

        try:
            db.session.commit()

            if is_new:
                self.on_created(item, params)
            else:
                self.on_reuploaded(item, params)
        finally:
            item.release_after_upload()

        logger.info(
            f"{self.ObjectType.__name__} added",
            extra={"dhash": item.dhash, "is_new": is_new},
        )
        schema = self.ItemResponseSchema()
        return schema.dump(item)


class ObjectResource(Resource):
    ObjectType = Object
    ListResponseSchema = ObjectListResponseSchema

    @requires_authorization
    def get(self):
        """
        ---
        summary: Search or list objects
        description: |
            Returns list of objects matching provided query,
            ordered from the latest one.
            If you want to fetch older objects use `older_than` parameter.

            Number of returned objects is limited by 'count' parameter
            (default value is 10).

            `Note:` Maximal number of returned objects is limited in
            MWDB's configuration (default value is 1 000)
        security:
            - bearerAuth: []
        tags:
            - object
        parameters:
            - in: query
              name: older_than
              schema:
                type: string
              description: |
                Fetch objects which are older than the object
                specified by identifier.

                Used for pagination
              required: false
            - in: query
              name: query
              schema:
                type: string
              description: Filter results using Lucene query
              required: false
            - in: query
              name: count
              schema:
                type: integer
              description: Number of objects to return
              required: false
              default: 10
        responses:
            200:
                description: List of objects
                content:
                  application/json:
                    schema: ObjectListResponseSchema
            400:
                description: |
                    When wrong parameters were provided
                    or syntax error occurred in Lucene query
            404:
                description: When user doesn't have access to the `older_than` object
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        if "page" in request.args:
            uses_deprecated_api(DeprecatedFeature.legacy_page_parameter)

        obj = load_schema(request.args, ObjectListRequestSchema())

        pivot_obj = None
        if obj["older_than"]:
            pivot_obj = Object.access(obj["older_than"])
            if pivot_obj is None:
                raise NotFound("Object specified in 'older_than' parameter not found")

        query = obj["query"]
        if query:
            try:
                db_query = build_query(query, queried_type=self.ObjectType)
            except QueryBaseException as e:
                raise BadRequest(str(e))
        else:
            db_query = db.session.query(self.ObjectType)

        limit = min(obj["count"], app_config.mwdb.listing_endpoints_count_limit)

        db_query = db_query.filter(
            g.auth_user.has_access_to_object(Object.id)
        ).order_by(Object.id.desc())
        if pivot_obj:
            db_query = db_query.filter(Object.id < pivot_obj.id)
        # Legacy parameter - to be removed in the future
        elif obj["page"] is not None and obj["page"] > 1:
            db_query = db_query.offset((obj["page"] - 1) * 10)

        objects = db_query.limit(limit).all()

        schema = self.ListResponseSchema()
        return schema.dump(objects, many=True)


class ObjectItemResource(Resource, ObjectUploader):
    ObjectType = Object
    ItemResponseSchema = ObjectItemResponseSchema
    ItemAndRelationsResponseSchema = ObjectItemAndRelationsResponseSchema
    CreateRequestSchema = None

    def call_specialised_remove_hook(self, obj):
        pass

    @requires_authorization
    def get(self, identifier):
        """
        ---
        summary: Get object information
        description: |
            Returns information about object
        security:
            - bearerAuth: []
        tags:
            - object
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: Object identifier
            - in: query
              name: exclude_relations
              schema:
                type: integer
              description: |
                If set, results doesn't include relations
                which will be default behavior on next major release of MWDB
              required: false
              default: 0
        responses:
            200:
                description: Information about object
                content:
                  application/json:
                    schema: ObjectItemResponseSchema
            404:
                description: |
                    When object doesn't exist or user doesn't have access
                    to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        args = load_schema(request.args, ObjectItemRequestSchema())
        obj = self.ObjectType.access(identifier)
        if obj is None:
            raise NotFound("Object not found")
        schema = (
            self.ItemResponseSchema()
            if args["exclude_relations"]
            else self.ItemAndRelationsResponseSchema()
        )
        return schema.dump(obj)

    def _get_upload_args(self, parent_identifier):
        """
        Transforms upload arguments mixed into various request fields
        """
        if request.is_json:
            # If request is application/json: all args are in JSON
            args = json.loads(request.get_data(parse_form_data=True, as_text=True))
        else:
            if "json" in request.form:
                # If request is multipart/form-data:
                # some args are in JSON and some are part of form
                args = json.loads(request.form["json"])
            else:
                args = {}
            if request.form.get("metakeys"):
                args["metakeys"] = request.form["metakeys"]
            if request.form.get("upload_as"):
                args["upload_as"] = request.form["upload_as"]
        args["parent"] = parent_identifier if parent_identifier != "root" else None
        return args

    @requires_authorization
    def post(self, identifier):
        if self.ObjectType is Object:
            raise MethodNotAllowed()

        schema = self.CreateRequestSchema()
        obj = load_schema(self._get_upload_args(identifier), schema)

        return self.create_object(obj)

    @requires_authorization
    def put(self, identifier):
        return self.post(identifier)

    @requires_authorization
    @requires_capabilities(Capabilities.removing_objects)
    def delete(self, identifier):
        """
        ---
        summary: Delete object
        description: |
            Removes an object from the database along with its references.

            Requires `removing_objects` capability.
        security:
            - bearerAuth: []
        tags:
            - object
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: Object identifier
        responses:
            200:
                description: When object was deleted
            403:
                description: When user doesn't have `removing_objects` capability
            404:
                description: |
                    When object doesn't exist or user doesn't have
                    access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        obj = self.ObjectType.access(identifier)

        if obj is None:
            raise NotFound("Object was not found")

        db.session.delete(obj)
        db.session.commit()

        self.call_specialised_remove_hook(obj)
        hooks.on_removed_object(obj)


class ObjectCountResource(Resource):
    @requires_authorization
    def get(self, type):
        """
        ---
        summary: Count objects
        description: |
            Returns number of objects matching provided query.
        security:
            - bearerAuth: []
        tags:
            - object
        parameters:
            - in: path
              name: type
              schema:
                type: string
                enum: [file, config, blob, object]
              description: Type of objects
            - in: query
              name: query
              schema:
                type: string
              description: Filter objects using Lucene query
              required: false
        responses:
            200:
                description: Number of objects
                content:
                  application/json:
                    schema: ObjectCountResponseSchema
            400:
                description: |
                    When wrong parameters were provided
                    or syntax error occurred in Lucene query
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = ObjectCountRequestSchema()
        obj = load_schema(request.args, schema)

        query = obj["query"]
        if query:
            try:
                db_query = build_query(query, queried_type=get_type_from_str(type))
            except QueryBaseException as e:
                raise BadRequest(str(e))
        else:
            db_query = db.session.query(get_type_from_str(type))

        db_query = db_query.filter(g.auth_user.has_access_to_object(Object.id))

        result = db_query.count()

        schema = ObjectCountResponseSchema()
        return schema.dump({"count": result})


class ObjectFavoriteResource(Resource):
    @requires_authorization
    @requires_capabilities(Capabilities.personalize)
    def put(self, identifier):
        """
        ---
        summary: Mark favorite object
        description: |
            Mark an object as a favorite for the user.

            Requires `personalize` capability.
        security:
            - bearerAuth: []
        tags:
            - object
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: Object identifier
        responses:
            200:
                description: Unmark favorite object
            400:
                description: When request body is invalid
            403:
                description: When user doesn't have `personalize` capability.
            404:
                description: When object doesn't exist.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """

        user = g.auth_user

        favorite_object = Object.access(identifier)

        if favorite_object is None:
            raise NotFound("Object not found")

        if favorite_object.favorite:
            logger.info(
                "Object is already marked as a favorite",
                extra={"user": user.login, "object_id": identifier},
            )
        else:
            favorite_object.followers.append(user)
            db.session.commit()
            logger.info(
                "Object marked as favorite",
                extra={"user": user.login, "object_id": identifier},
            )

    @requires_authorization
    @requires_capabilities(Capabilities.personalize)
    def delete(self, identifier):
        """
        ---
        summary: Unmark favorite object
        description: |
            Unmark an object as a favorite for the user.

            Requires `personalize` capability.
        security:
            - bearerAuth: []
        tags:
            - object
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: Object identifier
        responses:
            200:
                description: Unmark favorite object
            400:
                description: When request body is invalid
            403:
                description: When user doesn't have `personalize` capability.
            404:
                description: When object doesn't exist.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """

        user = g.auth_user

        favorite_object = Object.access(identifier)

        if favorite_object is None:
            raise NotFound("Object not found")

        if not favorite_object.favorite:
            logger.info(
                "Object is not marked as a favorite",
                extra={"user": user.login, "object_id": identifier},
            )
        else:
            favorite_object.followers.remove(user)
            db.session.commit()
            logger.info(
                "Object unmarked as favorite",
                extra={"user": user.login, "object_id": identifier},
            )


class ObjectShare3rdPartyResource(Resource):
    @requires_authorization
    @requires_capabilities(Capabilities.modify_3rd_party_sharing)
    def put(self, identifier):
        """
        ---
        summary: Mark object as shareable with third parties
        description: |
            Mark an object as shareable with third parties

            Requires `modify_3rd_party_sharing` capability.
        security:
            - bearerAuth: []
        tags:
            - object
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: Object identifier
        responses:
            200:
                description: |
                    Marked object as shareable or it was already marked as shareable
            400:
                description: When request body is invalid
            403:
                description: |
                    When user doesn't have `modify_3rd_party_sharing` capability.
            404:
                description: When object doesn't exist.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """

        selected_object = Object.access(identifier)

        if selected_object is None:
            raise NotFound("Object not found")

        selected_object.share_3rd_party = True
        db.session.commit()

        return
