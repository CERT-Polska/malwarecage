from flask import request, g
from flask_restful import Resource
from luqum.parser import ParseError
from werkzeug.exceptions import Forbidden, BadRequest, MethodNotAllowed, Conflict, NotFound

from model.object import AccessType
from plugin_engine import hooks
from model import db, Object, Group
from core.capabilities import Capabilities
from core.schema import ObjectShowBase, MetakeyShowSchema, MultiObjectSchema
from core.search import SQLQueryBuilder, SQLQueryBuilderBaseException

from . import logger, requires_authorization, requires_capabilities, access_object


class ObjectListResource(Resource):
    ObjectType = Object
    Schema = MultiObjectSchema
    SchemaKey = "objects"

    @requires_authorization
    def get(self):
        """
        ---
        summary: Search or list objects
        description: |
            Returns list of objects matching provided query, ordered from the latest one.

            Limited to 10 objects, use `older_than` parameter to fetch more.

            Don't rely on maximum count of returned objects because it can be changed/parametrized in future.
        security:
            - bearerAuth: []
        tags:
            - object
        parameters:
            - in: query
              name: older_than
              schema:
                type: string
              description: Fetch objects which are older than the object specified by identifier. Used for pagination
              required: false
            - in: query
              name: query
              schema:
                type: string
              description: Filter results using Lucene query
              required: false
        responses:
            200:
                description: List of objects
                content:
                  application/json:
                    schema: MultiObjectSchema
            400:
                description: When wrong parameters were provided or syntax error occured in Lucene query
            404:
                description: When user doesn't have access to the `older_than` object
        """
        if 'page' in request.args and 'older_than' in request.args:
            raise BadRequest("page and older_than can't be used simultaneously. Use `older_than` for new code.")

        if 'page' in request.args:
            logger.warning("'%s' used legacy 'page' parameter", g.auth_user.login)

        page = max(1, int(request.args.get('page', 1)))
        query = request.args.get('query')

        pivot_obj = None
        older_than = request.args.get('older_than')
        if older_than:
            pivot_obj = Object.access(older_than)
            if pivot_obj is None:
                raise NotFound("Object provided in 'older_than' not found")

        if query:
            try:
                db_query = SQLQueryBuilder().build_query(query, queried_type=self.ObjectType)
            except SQLQueryBuilderBaseException as e:
                raise BadRequest(str(e))
            except ParseError as e:
                raise BadRequest(str(e))
        else:
            db_query = db.session.query(self.ObjectType)

        db_query = (
            db_query.filter(g.auth_user.has_access_to_object(Object.id))
                    .order_by(Object.id.desc())
        )
        if pivot_obj:
            db_query = db_query.filter(Object.id < pivot_obj.id)
        # Legacy parameter - to be removed
        elif page > 1:
            db_query = db_query.offset((page - 1) * 10)

        db_query = db_query.limit(10)
        objects = db_query.all()

        schema = self.Schema()
        return schema.dump({self.SchemaKey: objects})


class ObjectResource(Resource):
    ObjectType = Object
    ObjectTypeStr = Object.__tablename__
    Schema = ObjectShowBase
    on_created = None
    on_reuploaded = None

    @requires_authorization
    def get(self, identifier):
        """
        ---
        summary: Get object
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
        responses:
            200:
                description: Information about object
                content:
                  application/json:
                    schema: ObjectShowBase
            404:
                description: When object doesn't exist or user doesn't have access to this object.
        """
        schema = self.Schema()
        obj = self.ObjectType.access(identifier)
        if obj is None:
            raise NotFound("Object not found")
        return schema.dump(obj)

    def create_object(self, obj):
        raise NotImplementedError()

    @requires_authorization
    def post(self, identifier):
        if self.ObjectType is Object:
            raise MethodNotAllowed()

        schema = self.Schema()

        if request.is_json:
            obj = schema.loads(request.get_data(parse_form_data=True, as_text=True))
        elif 'json' in request.form:
            obj = schema.loads(request.form["json"])
        else:
            obj = None

        if obj and obj.errors:
            return {"errors": obj.errors}, 400

        if identifier == 'root':
            parent_object = None
        else:
            if not g.auth_user.has_rights(Capabilities.adding_parents):
                raise Forbidden("You are not permitted to link with parent")
            parent_object = Object.access(identifier)
            if parent_object is None:
                raise NotFound("Parent object not found")

        metakeys = request.form.get('metakeys')
        upload_as = request.form.get("upload_as") or "*"

        if metakeys:
            metakeys = MetakeyShowSchema().loads(metakeys)
            if metakeys.errors:
                logger.warn('schema error', extra={
                    'error': metakeys.errors
                })
                raise BadRequest()
            metakeys = metakeys.data['metakeys']

        item, is_new = self.create_object(obj)

        if item is None:
            raise Conflict("Conflicting object types")

        if is_new:
            db.session.add(item)

        if metakeys:
            for metakey in metakeys:
                if item.add_metakey(metakey['key'], metakey['value'], commit=False) is None:
                    raise NotFound("Metakey '{}' not defined or insufficient "
                                   "permissions to set that one".format(metakey["key"]))

        if parent_object:
            item.add_parent(parent_object, commit=False)
            logger.info('relation added', extra={'parent': parent_object.dhash,
                                                 'child': item.dhash})

        if upload_as == "*":
            share_with = [group.id for group in g.auth_user.groups if group.name != "public"]
        else:
            if not g.auth_user.has_rights(Capabilities.sharing_objects) and \
               upload_as not in [group.name for group in g.auth_user.groups]:
                raise NotFound("Group {} doesn't exist".format(upload_as))
            group = Group.get_by_name(upload_as)
            if group is None:
                raise NotFound("Group {} doesn't exist".format(upload_as))
            share_with = [group.id, Group.get_by_name(g.auth_user.login).id]
            if group.pending_group is True:
                raise NotFound("Group {} is pending".format(upload_as))

        for share_group_id in share_with:
            item.give_access(share_group_id, AccessType.ADDED, item, g.auth_user, commit=False)

        if is_new:
            for all_access_group in Group.all_access_groups():
                item.give_access(all_access_group.id, AccessType.ADDED, item, g.auth_user, commit=False)

        db.session.commit()

        if is_new:
            hooks.on_created_object(item)
            if self.on_created:
                self.on_created(item)
        else:
            hooks.on_reuploaded_object(item)
            if self.on_reuploaded:
                self.on_reuploaded(item)

        logger.info('{} added'.format(self.ObjectTypeStr), extra={
            'dhash': item.dhash,
            'is_new': is_new
        })

        return schema.dump(item)

    @requires_authorization
    def put(self, identifier):
        # All should be PUT
        return self.post(identifier)


class ObjectChildResource(Resource):
    @requires_authorization
    @requires_capabilities(Capabilities.adding_parents)
    def put(self, type, parent, child):
        """
        ---
        summary: Link existing objects
        description: |
            Add new relation between existing objects.

            Requires `adding_parents` capability.
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
              description: Type of parent object
            - in: path
              name: parent
              description: Identifier of the parent object
              required: true
              schema:
                type: string
            - in: path
              name: child
              description: Identifier of the child object
              required: true
              schema:
                type: string
        responses:
            200:
                description: When relation was successfully added
            403:
                description: When user doesn't have `adding_parents` capability.
            404:
                description: When one of objects doesn't exist or user doesn't have access to object.
        """
        parent_object = access_object(type, parent)
        if parent_object is None:
            raise NotFound("Parent object not found")

        child_object = Object.access(child)
        if child_object is None:
            raise NotFound("Child object not found")

        child_object.add_parent(parent_object, commit=False)

        db.session.commit()
        logger.info('child added', extra={
            'parent': parent_object.dhash,
            'child': child_object.dhash
        })
