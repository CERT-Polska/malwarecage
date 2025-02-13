from marshmallow import Schema, fields

from .object import ObjectListItemResponseSchema


class RelationsResponseSchema(Schema):
    parents = fields.Nested(
        ObjectListItemResponseSchema,
        many=True,
        required=True,
        allow_none=False,
        attribute="accessible_parents",
    )
    children = fields.Nested(
        ObjectListItemResponseSchema,
        many=True,
        required=True,
        allow_none=False,
        attribute="limit_children",
    )
