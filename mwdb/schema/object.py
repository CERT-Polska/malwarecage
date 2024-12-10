import json

from marshmallow import (
    Schema,
    ValidationError,
    fields,
    post_dump,
    pre_load,
    validates_schema,
)

from .attribute import AttributeItemRequestSchema, AttributeItemResponseSchema
from .metakey import MetakeyItemRequestSchema
from .tag import TagItemResponseSchema, TagRequestSchema
from .utils import UTCDateTime


class ObjectListRequestSchema(Schema):
    page = fields.Int(missing=None)  # legacy, to be removed in future
    query = fields.Str(missing=None)
    older_than = fields.Str(missing=None)
    count = fields.Int(missing=10)

    @validates_schema
    def validate_key(self, data, **kwargs):
        if data["page"] is not None and data["older_than"] is not None:
            raise ValidationError(
                "'page' and 'older_than' can't be used simultaneously. "
                "Use 'older_than' for new code."
            )


class ObjectItemRequestSchema(Schema):
    exclude_relations = fields.Boolean(
        truthy={
            "1",
            "",
        },
        falsy={"0"},
        missing=False,
        allow_none=False,
    )


class ObjectCountRequestSchema(Schema):
    query = fields.Str(missing=None)


class ObjectCreateRequestSchemaBase(Schema):
    parent = fields.Str(missing=None)
    metakeys = fields.Nested(MetakeyItemRequestSchema, many=True, missing=[])
    attributes = fields.Nested(AttributeItemRequestSchema, many=True, missing=[])
    upload_as = fields.Str(missing="*", allow_none=False)
    karton_id = fields.UUID(missing=None)
    karton_arguments = fields.Dict(missing={}, keys=fields.Str())
    tags = fields.Nested(TagRequestSchema, many=True, missing=[])
    share_3rd_party = fields.Boolean(missing=True)


class ObjectLegacyMetakeysMixin(Schema):
    @pre_load
    def unpack_metakeys(self, params, **kwargs):
        """
        Metakeys are packed into JSON string that need to be deserialized first.
        Empty string in 'metakeys' field is treated like missing key.
        Request providing metakeys looks like this:
        `curl ... -F="metakeys='{"metakeys": [...]}'"`
        """
        params = dict(params)
        if "metakeys" in params:
            if params["metakeys"]:
                metakeys_json = json.loads(params["metakeys"])
                if "metakeys" not in metakeys_json:
                    raise ValidationError(
                        "Object provided to 'metakeys' field "
                        "must contain 'metakeys' key"
                    )
                params["metakeys"] = metakeys_json["metakeys"]
            else:
                del params["metakeys"]
        return params


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


class RelationsResponseSchema(Schema):
    parents = fields.Method("get_parents")
    children = fields.Nested(
        ObjectListItemResponseSchema, many=True, required=True, allow_none=False
    )

    def get_parents(self, obj):
        parents = obj.query_visible_parents().all()
        schema = ObjectListItemResponseSchema()
        return schema.dump(parents, many=True)


class ObjectItemAndRelationsResponseSchema(
    ObjectItemResponseSchema, RelationsResponseSchema
):
    """
    This is legacy schema that returns object item along with relations
    It is awfully slow when object is bound with lots of relatives
    """


class ObjectCountResponseSchema(Schema):
    count = fields.Int()
