from marshmallow import Schema, fields

from .config import ConfigItemResponseSchema
from .object import (
    ObjectCreateRequestSchemaBase,
    ObjectItemResponseSchema,
    ObjectListItemResponseSchema,
    ObjectListResponseSchemaBase,
)
from .utils import UTCDateTime


# Merge it with BlobCreateRequestSchema during legacy upload remove
class BlobCreateSpecSchema(Schema):
    blob_name = fields.Str(required=True, allow_none=False)
    blob_type = fields.Str(required=True, allow_none=False)
    content = fields.Str(required=True, allow_none=False)


class BlobCreateRequestSchema(ObjectCreateRequestSchemaBase, BlobCreateSpecSchema):
    pass


class BlobListItemResponseSchema(ObjectListItemResponseSchema):
    blob_name = fields.Str(required=True, allow_none=False)
    blob_size = fields.Int(required=True, allow_none=False)
    blob_type = fields.Str(required=True, allow_none=False)
    last_seen = UTCDateTime(required=True, allow_none=False)


class BlobListResponseSchema(ObjectListResponseSchemaBase, BlobListItemResponseSchema):
    __envelope_key__ = "blobs"


class BlobItemResponseSchema(ObjectItemResponseSchema):
    blob_name = fields.Str(required=True, allow_none=False)
    blob_size = fields.Int(required=True, allow_none=False)
    blob_type = fields.Str(required=True, allow_none=False)
    last_seen = UTCDateTime(required=True, allow_none=False)

    content = fields.Str(required=True, allow_none=False)
    latest_config = fields.Nested(
        ConfigItemResponseSchema, required=True, allow_none=True
    )
