from marshmallow import Schema, fields, post_dump

from .attribute import AttributeItemRequestSchema, AttributeItemResponseSchema
from .tag import TagItemResponseSchema, TagRequestSchema
from .utils import UTCDateTime


class ObjectListRequestSchema(Schema):
    query = fields.Str(missing=None)
    older_than = fields.Str(missing=None)
    count = fields.Int(missing=10)


class ObjectCountRequestSchema(Schema):
    query = fields.Str(missing=None)


class ObjectCreateRequestSchemaBase(Schema):
    parent = fields.Str(missing=None)
    attributes = fields.Nested(AttributeItemRequestSchema, many=True, missing=[])
    upload_as = fields.Str(missing="*", allow_none=False)
    karton_id = fields.UUID(missing=None)
    karton_arguments = fields.Dict(missing={}, keys=fields.Str())
    tags = fields.Nested(TagRequestSchema, many=True, missing=[])
    share_3rd_party = fields.Boolean(missing=True)


class ObjectListItemResponseSchema(Schema):
    id = fields.Str(attribute="dhash", required=True, allow_none=False)
    type = fields.Str(required=True, allow_none=False)
    tags = fields.Nested(
        TagItemResponseSchema, many=True, required=True, allow_none=False
    )
    upload_time = UTCDateTime(required=True, allow_none=False)


class ObjectListResponseSchemaBase(Schema):
    __envelope_key__ = "objects"

    @post_dump(pass_many=True)
    def wrap_with_envelope(self, data, many, **kwargs):
        if not many:
            raise ValueError("Schema supports only lists of objects")
        return {self.__envelope_key__: data}


class ObjectListResponseSchema(
    ObjectListResponseSchemaBase, ObjectListItemResponseSchema
):
    pass


class ObjectItemResponseSchema(Schema):
    id = fields.Str(attribute="dhash", required=True, allow_none=False)
    type = fields.Str(required=True, allow_none=False)
    tags = fields.Nested(
        TagItemResponseSchema, many=True, required=True, allow_none=False
    )
    upload_time = UTCDateTime(required=True, allow_none=False)
    favorite = fields.Boolean(required=True, allow_none=False)

    parents = fields.Nested(
        ObjectListItemResponseSchema,
        many=True,
        required=True,
        allow_none=False,
        attribute="accessible_parents",
    )
    children = fields.Nested(
        ObjectListItemResponseSchema, many=True, required=True, allow_none=False
    )
    attributes = fields.Nested(
        AttributeItemResponseSchema, many=True, required=True, allow_none=False
    )
    share_3rd_party = fields.Boolean(required=True, allow_none=False)

    @post_dump(pass_original=True)
    def get_accessible_attributes(self, data, object, **kwargs):
        """
        Replace all object attributes with attributes accessible for current user
        """
        object_attributes = object.get_attributes()
        schema = AttributeItemResponseSchema()
        attributes_serialized = schema.dump(object_attributes, many=True)
        return {**data, "attributes": attributes_serialized}


class ObjectCountResponseSchema(Schema):
    count = fields.Int()
