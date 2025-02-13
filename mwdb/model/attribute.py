from flask import g
from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

from mwdb.core.capabilities import Capabilities

from . import db


class Attribute(db.Model):
    __tablename__ = "attribute"
    __table_args__ = (
        # Assumes that JSONB key ordering is stable
        db.Index(
            "ix_attribute_unique",
            "object_id",
            "key",
            func.md5("value::text"),
            unique=True,
        ),
        db.Index("ix_attribute_value", "value", postgresql_using="gin"),
    )

    id = db.Column(db.Integer, primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey("object.id"), nullable=False)
    key = db.Column(
        db.String(64),
        db.ForeignKey("attribute_definition.key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    value = db.Column(JSONB, nullable=False)
    template = db.relationship("AttributeDefinition", lazy="joined")

    @property
    def label(self):
        return self.template.label

    @property
    def description(self):
        return self.template.description

    @classmethod
    def get(cls, object_id, key, value):
        return db.session.query(cls).filter(
            (cls.object_id == object_id)
            & (cls.key == key)
            & (cls.value == cast(value, JSONB))
        )

    @classmethod
    def get_by_id(cls, object_id, attribute_id):
        return db.session.query(cls).filter(
            (cls.object_id == object_id) & (cls.id == attribute_id)
        )

    @classmethod
    def get_or_create(cls, obj):
        """
        Polymophic get or create pattern, useful in dealing with race condition
        resulting in IntegrityError on the unique constraint.
         http://rachbelaid.com/handling-race-condition-insert-with-sqlalchemy/
        Returns tuple with object and boolean value if new object was created or not,
        True == new object
        """

        is_new = False
        new_cls = cls.get(obj.object_id, obj.key, obj.value).first()

        if new_cls is not None:
            return new_cls, is_new

        db.session.begin_nested()

        new_cls = obj
        try:
            db.session.add(new_cls)
            db.session.commit()
            is_new = True
        except IntegrityError:
            db.session.rollback()
            new_cls = cls.get(obj.object_id, obj.key, obj.value).first()
        return new_cls, is_new


class AttributePermission(db.Model):
    __tablename__ = "attribute_permission"

    key = db.Column(
        db.String(64),
        db.ForeignKey("attribute_definition.key", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("group.id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
        index=True,
    )
    __table_args__ = (
        db.Index(
            "ix_attribute_permission_attribute_group", "key", "group_id", unique=True
        ),
    )
    can_read = db.Column(db.Boolean, nullable=False)
    can_set = db.Column(db.Boolean, nullable=False)
    template = db.relationship(
        "AttributeDefinition",
        foreign_keys=[key],
        lazy="joined",
        back_populates="permissions",
    )
    group = db.relationship(
        "Group",
        foreign_keys=[group_id],
        lazy="joined",
        back_populates="attributes",
    )

    @property
    def group_name(self):
        return self.group.name


class AttributeDefinition(db.Model):
    __tablename__ = "attribute_definition"

    key = db.Column(db.String(64), primary_key=True)
    label = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=False)
    url_template = db.Column(db.Text, nullable=False)
    rich_template = db.Column(db.Text, nullable=False)
    # Example value used with rich_template
    example_value = db.Column(db.Text, nullable=False)
    hidden = db.Column(db.Boolean, nullable=False, default=False)
    permissions = db.relationship(
        "AttributePermission",
        lazy="joined",
        back_populates="template",
        cascade="all, delete",
    )
    attribute = db.relationship(
        "Attribute",
        back_populates="template",
        cascade="all, delete",
    )

    @staticmethod
    def query_for_read(key=None, include_hidden=False):
        """
        Prepares query for attribute keys that currently authenticated user can read

        :param key: Query for specific key (default: all matching keys)
        :param include_hidden: Include hidden keys
        """
        query = db.session.query(AttributeDefinition)

        if key is not None:
            query = query.filter(AttributeDefinition.key == key)

        if not include_hidden:
            query = query.filter(AttributeDefinition.hidden.isnot(True))

        if not g.auth_user.has_rights(Capabilities.reading_all_attributes):
            query = (
                query.join(AttributeDefinition.permissions)
                .filter(AttributePermission.can_read.is_(True))
                .filter(g.auth_user.is_member(AttributePermission.group_id))
            )
        return query

    @staticmethod
    def query_for_set(key=None):
        """
        Prepares query for attribute keys that currently authenticated user can set

        :param key: Query for specific key (default: all matching keys)
        """
        query = db.session.query(AttributeDefinition)

        if key is not None:
            query = query.filter(AttributeDefinition.key == key)

        if not g.auth_user.has_rights(Capabilities.adding_all_attributes):
            query = (
                query.join(AttributeDefinition.permissions)
                .filter(AttributePermission.can_set.is_(True))
                .filter(g.auth_user.is_member(AttributePermission.group_id))
            )
        return query
