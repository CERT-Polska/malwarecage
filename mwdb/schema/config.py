from marshmallow import Schema, fields

from .object import (
    ObjectCreateRequestSchemaBase,
    ObjectItemResponseSchema,
    ObjectListItemResponseSchema,
    ObjectListResponseSchemaBase,
)


class ConfigStatsRequestSchema(Schema):
    range = fields.Str(missing="*", allow_none=False)


# Merge it with ConfigCreateRequestSchema during legacy upload remove
class ConfigCreateSpecSchema(Schema):
    family = fields.Str(required=True, allow_none=False)
    config_type = fields.Str(missing="static", allow_none=False)
    cfg = fields.Dict(required=True, allow_none=False)


class ConfigCreateRequestSchema(ObjectCreateRequestSchemaBase, ConfigCreateSpecSchema):
    pass


class ConfigListItemResponseSchema(ObjectListItemResponseSchema):
    family = fields.Str(required=True, allow_none=False)
    config_type = fields.Str(required=True, allow_none=False)


class ConfigListResponseSchema(
    ObjectListResponseSchemaBase, ConfigListItemResponseSchema
):
    __envelope_key__ = "configs"


class ConfigLatestItemResponseSchema(ObjectListItemResponseSchema):
    """
    Limited ConfigItemResponseSchema that doesn't fetch relationships
    and other extra metadata.

    Used by FileItemResponseSchema.latest_config field.
    """

    family = fields.Str(required=True, allow_none=False)
    config_type = fields.Str(required=True, allow_none=False)
    cfg = fields.Dict(required=True, allow_none=False)


class ConfigItemResponseSchema(ObjectItemResponseSchema):
    family = fields.Str(required=True, allow_none=False)
    config_type = fields.Str(required=True, allow_none=False)
    cfg = fields.Dict(required=True, allow_none=False)


class ConfigStatsItemResponseSchema(Schema):
    family = fields.Str(required=True, allow_none=False)
    last_upload = fields.Date(required=True, allow_none=False)
    count = fields.Int(required=True, allow_none=False)


class ConfigStatsResponseSchema(Schema):
    families = fields.Nested(
        ConfigStatsItemResponseSchema, many=True, required=True, allow_none=False
    )
