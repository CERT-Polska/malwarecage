import json

from marshmallow import Schema, fields, pre_load

from .config import ConfigLatestItemResponseSchema
from .object import (
    ObjectCreateRequestSchemaBase,
    ObjectItemResponseSchema,
    ObjectListItemResponseSchema,
    ObjectListResponseSchemaBase,
)


class FileCreateRequestSchema(Schema):
    # BUG: https://github.com/marshmallow-code/marshmallow/issues/1042
    options = fields.Nested(
        ObjectCreateRequestSchemaBase, missing=ObjectCreateRequestSchemaBase().load({})
    )

    @pre_load
    def unpack_options(self, params, **kwargs):
        """
        Options are packed into JSON string that needs to be deserialized first.
        Empty string in 'options' field is treated like missing key.
        """
        params = dict(params)
        if "options" in params:
            if params["options"]:
                params["options"] = json.loads(params["options"])
            else:
                del params["options"]
        return params


class FileListItemResponseSchema(ObjectListItemResponseSchema):
    file_name = fields.Str(required=True, allow_none=False)
    file_size = fields.Int(required=True, allow_none=False)
    file_type = fields.Str(required=True, allow_none=False)

    md5 = fields.Str(required=True, allow_none=False)
    sha1 = fields.Str(required=True, allow_none=False)
    sha256 = fields.Str(required=True, allow_none=False)


class FileListResponseSchema(ObjectListResponseSchemaBase, FileListItemResponseSchema):
    __envelope_key__ = "files"


class FileItemResponseSchema(ObjectItemResponseSchema):
    file_name = fields.Str(required=True, allow_none=False)
    alt_names = fields.List(fields.Str(required=True, allow_none=False))
    file_size = fields.Int(required=True, allow_none=False)
    file_type = fields.Str(required=True, allow_none=False)

    md5 = fields.Str(required=True, allow_none=False)
    sha1 = fields.Str(required=True, allow_none=False)
    sha256 = fields.Str(required=True, allow_none=False)
    sha512 = fields.Str(required=True, allow_none=False)
    crc32 = fields.Str(required=True, allow_none=False)
    ssdeep = fields.Str(required=True, allow_none=True)

    latest_config = fields.Nested(
        ConfigLatestItemResponseSchema, required=True, allow_none=True
    )


class FileDownloadTokenResponseSchema(Schema):
    token = fields.Str(required=True, allow_none=False)
