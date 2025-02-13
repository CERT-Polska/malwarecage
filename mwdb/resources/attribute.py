from flask import g, request
from werkzeug.exceptions import BadRequest, Conflict, Forbidden, NotFound

from mwdb.core.capabilities import Capabilities
from mwdb.core.plugins import hooks
from mwdb.core.service import Resource
from mwdb.model import Attribute, AttributeDefinition, AttributePermission, Group, db
from mwdb.schema.attribute import (
    AttributeDefinitionCreateRequestSchema,
    AttributeDefinitionItemResponseSchema,
    AttributeDefinitionListRequestSchema,
    AttributeDefinitionListResponseSchema,
    AttributeDefinitionUpdateRequestSchema,
    AttributeItemRequestSchema,
    AttributeListRequestSchema,
    AttributeListResponseSchema,
    AttributePermissionDeleteRequestSchema,
    AttributePermissionItemResponseSchema,
    AttributePermissionListResponseSchema,
    AttributePermissionUpdateRequestSchema,
)

from . import (
    access_object,
    load_schema,
    loads_schema,
    logger,
    requires_authorization,
    requires_capabilities,
)


class AttributeListResource(Resource):
    @requires_authorization
    def get(self, type, identifier):
        """
        ---
        summary: Get object attributes
        description: |
            Returns all attributes of specified object that user is allowed to read.
        security:
            - bearerAuth: []
        tags:
            - attribute
        parameters:
            - in: path
              name: type
              schema:
                type: string
                enum: [file, config, blob, object]
              description: Type of object
            - in: path
              name: identifier
              schema:
                type: string
              description: Object identifier
            - in: query
              name: hidden
              schema:
                type: int
              description: |
                Show hidden attributes
                (requires `reading_all_attributes` capability)
              required: false
        responses:
            200:
                description: Object attributes
                content:
                  application/json:
                    schema: AttributeListResponseSchema
            403:
                description: |
                    When user requested hidden attributes
                    but doesn't have `reading_all_attributes` capability
            404:
                description: |
                    When object doesn't exist or user doesn't have
                    access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = AttributeListRequestSchema()
        obj = load_schema(request.args, schema)

        show_hidden = obj["hidden"]
        if show_hidden and not g.auth_user.has_rights(
            Capabilities.reading_all_attributes
        ):
            raise Forbidden("You are not permitted to read hidden attributes")

        db_object = access_object(type, identifier)
        if db_object is None:
            raise NotFound("Object not found")

        attributes = db_object.get_attributes(show_hidden=show_hidden)
        schema = AttributeListResponseSchema()
        return schema.dump({"attributes": attributes})

    @requires_authorization
    def post(self, type, identifier):
        """
        ---
        summary: Add object attribute
        description: |
            Adds attribute to specified object.

            User must have `set` access to the attribute key
            or `adding_all_attributes` capability.
        security:
            - bearerAuth: []
        tags:
            - attribute
        parameters:
            - in: path
              name: type
              schema:
                type: string
                enum: [file, config, blob, object]
              description: Type of object
            - in: path
              name: identifier
              schema:
                type: string
              description: Object identifier
        requestBody:
            description: Attribute key and value
            content:
              application/json:
                schema: AttributeItemRequestSchema
        responses:
            200:
                description: When attribute was added successfully
                content:
                  application/json:
                    schema: AttributeListResponseSchema
            404:
                description: |
                    When object doesn't exist or user doesn't have
                    access to this object.

                    When attribute key is not defined or user doesn't have
                    privileges to set that one.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = AttributeItemRequestSchema()
        obj = loads_schema(request.get_data(as_text=True), schema)

        db_object = access_object(type, identifier)
        if db_object is None:
            raise NotFound("Object not found")

        key = obj["key"]
        value = obj["value"]
        is_new = db_object.add_attribute(key, value)
        if is_new is None:
            raise NotFound(
                f"Attribute '{key}' is not defined or you have "
                f"insufficient permissions to set it"
            )

        db.session.commit()
        db.session.refresh(db_object)
        attributes = db_object.get_attributes()
        attribute = next((attr for attr in attributes if attr.key == key), None)
        if is_new:
            hooks.on_created_attribute(db_object, attribute)
            hooks.on_changed_object(db_object)
        schema = AttributeListResponseSchema()
        return schema.dump({"attributes": attributes})


class AttributeResource(Resource):
    @requires_authorization
    @requires_capabilities("removing_attributes")
    def delete(self, type, identifier, attribute_id):
        """
        ---
        summary: Delete object attribute
        description: |
            Deletes attribute from specified object.

            User must have `removing_attributes` capability.
        security:
            - bearerAuth: []
        tags:
            - attribute
        parameters:
            - in: path
              name: type
              schema:
                type: string
                enum: [file, config, blob, object]
              description: Type of object
            - in: path
              name: identifier
              schema:
                type: string
              description: Object identifier
            - in: path
              name: attribute_id
              schema:
                type: string
              description: Identifier of attribute to be deleted
              required: true
        responses:
            200:
                description: When attribute was deleted successfully
            404:
                description: |
                    When object doesn't exist or user doesn't have access
                    to this object.
                    When attribute key is not defined or user doesn't have privileges
                    to set that one.
                    When attribute is already deleted
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        db_object = access_object(type, identifier)
        if db_object is None:
            raise NotFound("Object not found")

        attribute_to_delete = Attribute.get_by_id(db_object.id, attribute_id).first()
        is_deleted = db_object.remove_attribute_by_id(attribute_id)
        if is_deleted is False:
            raise NotFound(
                "Attribute is not defined or you have "
                "insufficient permissions to delete it"
            )
        db.session.commit()
        hooks.on_removed_attribute(db_object, attribute_to_delete)
        hooks.on_changed_object(db_object)


class AttributeDefinitionListResource(Resource):
    @requires_authorization
    def get(self):
        """
        ---
        summary: Get list of attribute keys
        description: |
            Returns list of attribute key definitions.
        security:
            - bearerAuth: []
        tags:
            - attribute
        parameters:
            - in: query
              name: access
              schema:
                type: string
                enum: [read, set, manage]
                default: read
              description: Type of desired access
        responses:
            200:
                description: List of attribute key definitions
                content:
                  application/json:
                    schema: AttributeDefinitionListResponseSchema
            400:
                description: When used unknown access type
            403:
                description: |
                    When requested `manage` access
                    but user doesn't have 'manage_users' capability
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = AttributeDefinitionListRequestSchema()
        obj = load_schema(request.args, schema)
        access = obj["access"]

        if access == "read":
            attribute_definitions = AttributeDefinition.query_for_read()
        elif access == "set":
            attribute_definitions = AttributeDefinition.query_for_set()
        elif access == "manage":
            if not g.auth_user.has_rights(Capabilities.manage_users):
                raise Forbidden("You are not permitted to manage attributes")
            attribute_definitions = db.session.query(AttributeDefinition)
        else:
            raise BadRequest(f"Unknown desired access type '{access}'")

        attribute_definitions = attribute_definitions.order_by(
            AttributeDefinition.key
        ).all()
        schema = AttributeDefinitionListResponseSchema()
        return schema.dump({"attribute_definitions": attribute_definitions})

    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def post(self):
        """
        ---
        summary: Create attribute key
        description: |
            Creates attribute key definition.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - attribute
        requestBody:
            description: Attribute key definition
            content:
              application/json:
                schema: AttributeDefinitionCreateRequestSchema
        responses:
            200:
                description: When attribute definition is successfully added
                content:
                  application/json:
                    schema: AttributeDefinitionItemResponseSchema
            400:
                description: |
                    When one of attribute definition fields is missing or incorrect.
            403:
                description: When user doesn't have `manage_users` capability.
            409:
                description: If attribute key is already defined
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = AttributeDefinitionCreateRequestSchema()
        obj = loads_schema(request.get_data(as_text=True), schema)

        attribute_definition = (
            db.session.query(AttributeDefinition).filter(
                AttributeDefinition.key == obj["key"]
            )
        ).first()

        if attribute_definition:
            raise Conflict(f"Attribute key '{obj['key']}' is already defined")

        attribute_definition = AttributeDefinition(
            key=obj["key"],
            url_template=obj["url_template"],
            rich_template=obj["rich_template"],
            example_value=obj["example_value"],
            label=obj["label"],
            description=obj["description"],
            hidden=obj["hidden"],
        )
        db.session.add(attribute_definition)
        db.session.commit()

        hooks.on_created_attribute_key(attribute_definition)
        schema = AttributeDefinitionItemResponseSchema()
        return schema.dump(attribute_definition)


class AttributeDefinitionResource(Resource):
    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def get(self, key):
        """
        ---
        summary: Get attribute key details
        description: |
            Returns attribute key definition details.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - attribute
        parameters:
            - in: path
              name: key
              schema:
                type: string
              description: Attribute key
        responses:
            200:
                description: Attribute key definition
                content:
                  application/json:
                    schema: AttributeDefinitionItemResponseSchema
            403:
                description: When user doesn't have `manage_users` capability.
            404:
                description: When specified attribute key doesn't exist
            503:
                description: |
                   Request canceled due to database statement timeout.
        """
        attribute_definition = (
            db.session.query(AttributeDefinition)
            .filter(AttributeDefinition.key == key)
            .first()
        )
        if attribute_definition is None:
            raise NotFound("No such attribute key")
        schema = AttributeDefinitionItemResponseSchema()
        return schema.dump(attribute_definition)

    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def put(self, key):
        """
        ---
        summary: Update attribute key
        description: |
            Update attribute key definition.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - attribute
        parameters:
            - in: path
              name: key
              schema:
                type: string
              description: Attribute key
        requestBody:
            description: Attribute definition to update
            content:
              application/json:
                schema: AttributeDefinitionUpdateRequestSchema
        responses:
            200:
                description: When attribute definition is successfully updated
                content:
                  application/json:
                    schema: AttributeDefinitionItemResponseSchema
            400:
                description: |
                    When one of attribute definition fields are missing or incorrect.
            403:
                description: When user doesn't have `manage_users` capability.
            404:
                description: When attribute doesn't exist.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = AttributeDefinitionUpdateRequestSchema()
        obj = loads_schema(request.get_data(as_text=True), schema)

        attribute_definition = (
            db.session.query(AttributeDefinition)
            .filter(AttributeDefinition.key == key)
            .first()
        )
        if attribute_definition is None:
            raise NotFound("No such attribute")

        label = obj["label"]
        if label is not None:
            attribute_definition.label = label

        description = obj["description"]
        if description is not None:
            attribute_definition.description = description

        url_template = obj["url_template"]
        if url_template is not None:
            attribute_definition.url_template = url_template

        rich_template = obj["rich_template"]
        if rich_template is not None:
            attribute_definition.rich_template = rich_template

        example_value = obj["example_value"]
        if example_value is not None:
            attribute_definition.example_value = example_value

        hidden = obj["hidden"]
        if hidden is not None:
            attribute_definition.hidden = obj["hidden"]

        db.session.commit()
        logger.info("Attribute updated", extra=obj)
        hooks.on_updated_attribute_key(attribute_definition)

        schema = AttributeDefinitionItemResponseSchema()
        return schema.dump(attribute_definition)

    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def delete(self, key):
        """
        ---
        summary: Delete attribute key
        description: |
            Deletes attribute key including all related object attributes.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - attribute
        parameters:
            - in: path
              name: key
              schema:
                type: string
              description: Attribute key
        responses:
            200:
                description: When attribute key was deleted
            403:
                description: When user doesn't have `manage_users` capability.
            404:
                description: When specified attribute key doesn't exist
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        attribute_definition = (
            db.session.query(AttributeDefinition)
            .filter(AttributeDefinition.key == key)
            .first()
        )
        if attribute_definition is None:
            raise NotFound("No such attribute key")
        db.session.delete(attribute_definition)
        db.session.commit()
        hooks.on_removed_attribute_key(attribute_definition)


class AttributePermissionResource(Resource):
    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def get(self, key):
        """
        ---
        summary: Get attribute key permission list
        description: |
            Returns group access control list for specified
            attribute key

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - attribute
        parameters:
            - in: path
              name: key
              schema:
                type: string
              description: Attribute key
        responses:
            200:
                description: List of group permissions
                content:
                  application/json:
                    schema: AttributePermissionListResponseSchema
            403:
                description: When user doesn't have `manage_users` capability.
            404:
                description: When attribute key doesn't exist
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        attribute_definition = (
            db.session.query(AttributeDefinition)
            .filter(AttributeDefinition.key == key)
            .first()
        )
        if attribute_definition is None:
            raise NotFound("No such attribute key")

        schema = AttributePermissionListResponseSchema()
        return schema.dump({"attribute_permissions": attribute_definition.permissions})

    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def put(self, key):
        """
        ---
        summary: Add/modify attribute key permission
        description: |
            Adds or modifies attribute key group permission
            for specified key and group name.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - attribute
        parameters:
            - in: path
              name: key
              schema:
                type: string
              description: Attribute key
        requestBody:
            description: Attribute key permission definition
            content:
                application/json:
                  schema: AttributePermissionUpdateRequestSchema
        responses:
            200:
                description: When group permission has been successfully changed
                content:
                  application/json:
                    schema: AttributePermissionItemResponseSchema
            400:
                description: |
                    When one of attribute permission fields is missing or incorrect.
            403:
                description: When user doesn't have `manage_users` capability.
            404:
                description: When attribute key or group doesn't exist
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = AttributePermissionUpdateRequestSchema()
        obj = loads_schema(request.get_data(as_text=True), schema)

        attribute_definition = (
            db.session.query(AttributeDefinition)
            .filter(AttributeDefinition.key == key)
            .first()
        )
        if attribute_definition is None:
            raise NotFound("No such attribute key")

        group = db.session.query(Group).filter(Group.name == obj["group_name"]).first()
        if group is None:
            raise NotFound("No such group")

        attribute_permission = AttributePermission(
            key=key,
            group_id=group.id,
            can_read=obj["can_read"],
            can_set=obj["can_set"],
        )
        db.session.merge(attribute_permission)
        db.session.commit()

        schema = AttributePermissionItemResponseSchema()
        return schema.dump(attribute_permission)

    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def delete(self, key):
        """
        ---
        summary: Delete attribute key permission
        description: |
            Removes attribute key permission for specified key and group name.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - attribute
        parameters:
            - in: path
              name: key
              schema:
                type: string
              description: Attribute key
            - in: query
              name: group_name
              schema:
                type: string
              description: Group name to remove
        responses:
            200:
                description: When group permission has been successfully removed
            403:
                description: When user doesn't have `manage_users` capability.
            404:
                description: |
                    When attribute key or group or group permission doesn't exist
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = AttributePermissionDeleteRequestSchema()
        obj = load_schema(request.args, schema)

        group = db.session.query(Group).filter(Group.name == obj["group_name"]).first()
        if group is None:
            raise NotFound("No such group")

        attribute_permission = (
            db.session.query(AttributePermission)
            .filter(
                AttributePermission.key == key,
                AttributePermission.group_id == group.id,
            )
            .first()
        )

        if attribute_permission is None:
            raise NotFound("No such attribute permission")

        db.session.delete(attribute_permission)
        db.session.commit()
