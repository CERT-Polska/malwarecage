from datetime import datetime, timedelta

from flask import g, request
from sqlalchemy import func
from werkzeug.exceptions import BadRequest, Conflict, Forbidden, NotFound

from mwdb.core.capabilities import Capabilities
from mwdb.core.deprecated import DeprecatedFeature, deprecated_endpoint
from mwdb.core.plugins import hooks
from mwdb.core.service import Resource
from mwdb.model import Config, TextBlob, db
from mwdb.model.object import ObjectTypeConflictError
from mwdb.schema.blob import BlobCreateSpecSchema
from mwdb.schema.config import (
    ConfigCreateRequestSchema,
    ConfigItemAndRelationsResponseSchema,
    ConfigItemResponseSchema,
    ConfigLegacyCreateRequestSchema,
    ConfigListResponseSchema,
    ConfigStatsRequestSchema,
    ConfigStatsResponseSchema,
)

from . import load_schema, loads_schema, requires_authorization, requires_capabilities
from .object import ObjectItemResource, ObjectResource, ObjectUploader


class ConfigStatsResource(Resource):
    @requires_authorization
    def get(self):
        """
        ---
        summary: Get config statistics
        description: |
            Get static configuration global statistics grouped per malware family.
        security:
            - bearerAuth: []
        tags:
            - config
        parameters:
            - in: query
              name: range
              schema:
                type: string
              description: Time range in hours `24h`, days `2d` or all time `*`
              default: '*'
              required: false
        responses:
            200:
                description: Static configuration global statistics
                content:
                  application/json:
                    schema: ConfigStatsResponseSchema
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = ConfigStatsRequestSchema()
        params = load_schema(request.args, schema)

        from_time = params["range"]
        if from_time.endswith("h"):
            from_time = int(from_time[:-1])
        elif from_time.endswith("d"):
            from_time = int(from_time[:-1]) * 24
        elif from_time != "*":
            raise BadRequest("Wrong range format")

        query = db.session.query(
            Config.family, func.max(Config.upload_time).label("maxdate"), func.count()
        ).group_by(Config.family)

        if from_time != "*":
            query = query.filter(
                Config.upload_time > (datetime.now() - timedelta(hours=from_time))
            )

        families = [
            {"family": family, "last_upload": upload_time, "count": count}
            for family, upload_time, count in query.all()
        ]

        schema = ConfigStatsResponseSchema()
        return schema.dump({"families": families})


class ConfigUploader(ObjectUploader):
    def on_created(self, object, params):
        super().on_created(object, params)
        hooks.on_created_config(object)

    def on_reuploaded(self, object, params):
        super().on_reuploaded(object, params)
        hooks.on_reuploaded_config(object)

    def _get_embedded_blob(self, in_blob, share_with, attributes, share_3rd_party):
        if isinstance(in_blob, dict):
            schema = BlobCreateSpecSchema()
            blob_spec = load_schema(in_blob, schema)

            try:
                blob_obj, is_new = TextBlob.get_or_create(
                    blob_spec["content"],
                    blob_spec["blob_name"],
                    blob_spec["blob_type"],
                    share_3rd_party=share_3rd_party,
                    parent=None,
                    share_with=share_with,
                    attributes=attributes,
                )
            except ObjectTypeConflictError:
                raise Conflict("Object already exists and is not a blob")
            return blob_obj
        elif isinstance(in_blob, str):
            blob_obj = TextBlob.access(in_blob)
            if not blob_obj:
                raise NotFound(f"Blob {in_blob} doesn't exist")
            return blob_obj
        else:
            raise BadRequest(
                "'in-blob' key must be set to blob SHA256 hash or blob specification"
            )

    def _create_object(
        self, spec, parent, share_with, attributes, analysis_id, tags, share_3rd_party
    ):
        try:
            blobs = []
            config = dict(spec["cfg"])

            for first, second in config.items():
                if isinstance(second, dict) and list(second.keys()) == ["in-blob"]:
                    if not g.auth_user.has_rights(Capabilities.adding_blobs):
                        raise Forbidden("You are not permitted to add blob objects")
                    blob_obj = self._get_embedded_blob(
                        second["in-blob"], share_with, attributes, share_3rd_party
                    )
                    config[first]["in-blob"] = blob_obj.dhash
                    blobs.append(blob_obj)
                elif isinstance(second, dict) and ("in-blob" in list(second.keys())):
                    raise BadRequest("'in-blob' should be the only key")

            obj, is_new = Config.get_or_create(
                config,
                spec["family"],
                share_3rd_party=share_3rd_party,
                config_type=spec["config_type"],
                parent=parent,
                share_with=share_with,
                attributes=attributes,
                analysis_id=analysis_id,
                tags=tags,
            )

            for blob in blobs:
                blob.add_parent(obj, commit=False)

            return obj, is_new
        except ObjectTypeConflictError:
            raise Conflict("Object already exists and is not a config")


class ConfigResource(ObjectResource, ConfigUploader):

    ObjectType = Config
    ListResponseSchema = ConfigListResponseSchema
    ItemResponseSchema = ConfigItemResponseSchema
    ItemAndRelationsResponseSchema = ConfigItemAndRelationsResponseSchema

    @requires_authorization
    def get(self):
        """
        ---
        summary: Search or list configs
        description: |
            Returns list of configs matching provided query,
            ordered from the latest one.
            If you want to fetch older configs use `older_than` parameter.

            Number of returned configs is limited by 'count' parameter
            (default value is 10).

            `Note:` Maximal number of returned configs is limited in
            MWDB's configuration (default value is 1 000)
        security:
            - bearerAuth: []
        tags:
            - config
        parameters:
            - in: query
              name: older_than
              schema:
                type: string
              description: |
                Fetch configs which are older than the object specified by identifier.
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
                description: List of configs
                content:
                  application/json:
                    schema: ConfigListResponseSchema
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
        return super().get()

    @requires_authorization
    @requires_capabilities(Capabilities.adding_configs)
    def post(self):
        """
        ---
        summary: Upload config
        description: |
            Uploads a new config.

            Requires `adding_configs` capability.
        security:
            - bearerAuth: []
        tags:
            - config
        requestBody:
            required: true
            description: Configuration to be uploaded
            content:
              application/json:
                schema: ConfigCreateRequestSchema
                examples:
                  simple:
                    summary: Simple configuration upload
                    value:
                      cfg:
                        family: malwarex
                        urls: ["http://evil.local"]
                      family: malwarex
                  full:
                    summary: Fully-featured configuration upload
                    value:
                      cfg:
                        family: malwarex
                        urls: ["http://evil.local"]
                      family: malwarex
                      config_type: static
                      parent: null
                      upload_as: "*"
                      metakeys:
                       - key: string
                         value: string
                      attributes:
                       - key: string
                         value: string
                      tags:
                       - tag: string
                      karton_id: string
                      karton_arguments:
                       string: string
        responses:
            200:
                description: Information about uploaded config
                content:
                  application/json:
                    schema: ConfigItemResponseSchema
            403:
                description: |
                    No permissions to perform additional operations
                    (e.g. adding parent, metakeys)
            404:
                description: |
                    One of attribute keys doesn't exist
                    or user doesn't have permission to set it.

                    Specified `upload_as` group doesn't exist
                    or user doesn't have permission to share objects with that group
            409:
                description: Object exists yet but has different type
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = ConfigCreateRequestSchema()
        obj = loads_schema(request.get_data(as_text=True), schema)

        return self.create_object(obj)


class ConfigItemResource(ObjectItemResource, ConfigUploader):

    ObjectType = Config
    ItemResponseSchema = ConfigItemResponseSchema
    ItemAndRelationsResponseSchema = ConfigItemAndRelationsResponseSchema
    CreateRequestSchema = ConfigLegacyCreateRequestSchema

    def call_specialised_remove_hook(self, config):
        hooks.on_removed_config(config)

    @requires_authorization
    def get(self, identifier):
        """
        ---
        summary: Get config
        description: |
            Returns config information and contents.
        security:
            - bearerAuth: []
        tags:
            - config
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: Config identifier
        responses:
            200:
                description: Config information and contents
                content:
                  application/json:
                    schema: ConfigItemResponseSchema
            404:
                description: |
                    When config doesn't exist, object is not a config
                    or user doesn't have access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        return super().get(identifier)

    @deprecated_endpoint(DeprecatedFeature.legacy_object_upload)
    @requires_authorization
    @requires_capabilities(Capabilities.adding_configs)
    def put(self, identifier):
        """
        ---
        summary: Upload config
        description: |
            Uploads a new config.

            Requires `adding_configs` capability.

            Deprecated: use POST /config method instead.
        security:
            - bearerAuth: []
        deprecated: true
        tags:
            - config
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              default: root
              description: |
                Parent object identifier or `root` if there is no parent.

                User must have `adding_parents` capability to specify a parent object.
        requestBody:
            required: true
            content:
              multipart/form-data:
                schema:
                  type: object
                  description: |
                    Configuration to be uploaded with additional parameters
                    (verbose mode)
                  properties:
                    json:
                      type: object
                      properties:
                          family:
                             type: string
                          config_type:
                             type: string
                             default: static
                          cfg:
                             type: object
                      description: JSON-encoded config object specification
                    metakeys:
                      type: object
                      properties:
                          metakeys:
                            type: array
                            items:
                                $ref: '#/components/schemas/MetakeyItemRequest'
                      description: |
                        Attributes to be added after file upload

                        User must be allowed to set specified attribute keys.
                    upload_as:
                      type: string
                      default: '*'
                      description: |
                        Group that object will be shared with.

                        If user doesn't have `sharing_with_all` capability,
                        user must be a member of specified group
                        (unless `Group doesn't exist` error will occur).

                        If default value `*` is specified - object will be
                        exclusively shared with all user's groups excluding `public`.
                  required:
                    - json
              application/json:
                schema: ConfigCreateSpecSchema
        responses:
            200:
                description: Information about uploaded config
                content:
                  application/json:
                    schema: ConfigItemResponseSchema
            403:
                description: |
                    No permissions to perform additional operations
                    (e.g. adding parent, metakeys)
            404:
                description: |
                    One of attribute keys doesn't exist or
                    user doesn't have permission to set it.

                    Specified `upload_as` group doesn't exist or
                    user doesn't have permission to share objects
                    with that group
            409:
                description: Object exists yet but has different type
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        return super().put(identifier)

    @requires_authorization
    @requires_capabilities(Capabilities.removing_objects)
    def delete(self, identifier):
        """
        ---
        summary: Delete config
        description: |
            Removes a config from the database along with its references.

            Requires `removing_objects` capability.
        security:
            - bearerAuth: []
        tags:
            - config
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: Config identifier
        responses:
            200:
                description: When config was deleted
            403:
                description: When user doesn't have `removing_objects` capability
            404:
                description: |
                    When config doesn't exist, object is not a config or
                    user doesn't have access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        return super().delete(identifier)
