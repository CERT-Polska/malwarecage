import datetime
import os
from typing import Optional, Tuple

import bcrypt
from flask import g
from sqlalchemy import and_
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.exc import NoResultFound

from mwdb.core.auth import AuthScope, generate_token, verify_token
from mwdb.core.capabilities import Capabilities

from . import db
from .group import Group, Member
from .oauth import OpenIDUserIdentity
from .object import ObjectPermission, favorites


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    login = db.Column(db.String(32), index=True, unique=True, nullable=False)
    email = db.Column(db.String(128), nullable=False)

    password_hash = db.Column(db.String(128))
    # Password version (set password link and session token validation)
    # Invalidates set password link or session when password has been changes
    password_ver = db.Column(db.String(16))
    # Identity version (session token validation)
    # Invalidates session when user capabilities has been changed
    identity_ver = db.Column(db.String(16))

    additional_info = db.Column(db.String, nullable=False)
    disabled = db.Column(db.Boolean, default=False, nullable=False)
    pending = db.Column(db.Boolean, default=False, nullable=False)

    requested_on = db.Column(db.DateTime)
    registered_on = db.Column(db.DateTime)
    registered_by = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    logged_on = db.Column(db.DateTime)
    set_password_on = db.Column(db.DateTime)

    memberships = db.relationship(
        Member, back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    groups = association_proxy(
        "memberships", "group", creator=lambda group: Member(group=group)
    )
    openid_identities = db.relationship(
        OpenIDUserIdentity,
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    permissions = db.relationship(
        "ObjectPermission",
        back_populates="related_user",
    )
    favorites = db.relationship(
        "Object", secondary=favorites, back_populates="followers"
    )

    commented_objects = db.relationship(
        "Object",
        secondary="comment",
        back_populates="comment_authors",
        viewonly=True,
    )

    comments = db.relationship(
        "Comment",
        back_populates="author",
    )

    quick_queries = db.relationship(
        "QuickQuery", back_populates="owner", cascade="all, delete"
    )

    api_keys = db.relationship(
        "APIKey", foreign_keys="APIKey.user_id", backref="user", cascade="all, delete"
    )
    registrar = db.relationship(
        "User",
        foreign_keys="User.registered_by",
        remote_side=[id],
        uselist=False,
    )

    # used to load-balance the malware processing pipeline
    feed_quality = db.Column(db.String(32), nullable=False, server_default="high")

    @property
    def group_names(self):
        return [group.name for group in self.groups]

    @property
    def registrar_login(self):
        return self.registrar and self.registrar.login

    @property
    def capabilities(self):
        return set.union(*[set(group.capabilities) for group in self.groups])

    def has_rights(self, perms):
        return perms in self.capabilities

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(12)
        ).decode("utf-8")
        self.password_ver = os.urandom(8).hex()
        self.set_password_on = datetime.datetime.utcnow()

    def reset_sessions(self):
        # Should be also called for fresh user objects
        self.identity_ver = os.urandom(8).hex()

    def verify_password(self, password):
        if self.password_hash is None:
            return False
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    @staticmethod
    def create(
        login, email, additional_info, pending=False, feed_quality=None, commit=True
    ):
        from mwdb.model.group import Group

        # Create user's private group
        user_group = Group(name=login, private=True, immutable=True)
        db.session.add(user_group)

        # Create user object
        user = User(
            login=login,
            email=email,
            additional_info=additional_info,
            feed_quality=feed_quality or "high",
            pending=pending,
            disabled=False,
            groups=[user_group] + Group.all_default_groups(),
        )
        user.reset_sessions()

        if not pending:
            if not g.auth_user:
                user.registered_by = None
            else:
                user.registered_by = g.auth_user.id
            user.registered_on = datetime.datetime.utcnow()
        else:
            user.requested_on = datetime.datetime.utcnow()

        db.session.add(user)
        if commit:
            db.session.commit()
        return user

    def _generate_token(self, user_fields, scope, expiration, **extra_fields):
        token_data = {"login": self.login, **extra_fields}
        for field in user_fields:
            token_data[field] = getattr(self, field)
        token = generate_token(
            token_data,
            scope,
            expiration,
        )
        return token

    @staticmethod
    def _verify_token(token, fields, scope) -> Optional[Tuple["User", Optional[str]]]:
        data = verify_token(token, scope)
        if data is None:
            return None

        try:
            user_obj = User.query.filter(User.login == data["sub"]).one()
        except NoResultFound:
            return None

        for field in fields:
            if field not in data:
                return None
            if data[field] != getattr(user_obj, field):
                return None

        return user_obj, data.get("provider")

    def generate_session_token(self, provider=None):
        return self._generate_token(
            ["password_ver", "identity_ver"],
            scope=AuthScope.session,
            expiration=24 * 3600,
            provider=provider,
        )

    def generate_set_password_token(self):
        return self._generate_token(
            ["password_ver"],
            scope=AuthScope.set_password,
            expiration=14 * 24 * 3600,
        )

    @staticmethod
    def verify_session_token(token) -> Optional[Tuple["User", Optional[str]]]:
        return User._verify_token(
            token,
            ["password_ver", "identity_ver"],
            scope=AuthScope.session,
        )

    @staticmethod
    def verify_set_password_token(token) -> Optional["User"]:
        result = User._verify_token(
            token,
            ["password_ver"],
            scope=AuthScope.set_password,
        )
        return None if result is None else result[0]

    def is_member(self, group_id):
        groups = db.session.query(Member.group_id).filter(Member.user_id == self.id)
        return group_id.in_(groups)

    def is_group_admin(self, group_id):
        group = (
            db.session.query(Member).filter(
                Member.user_id == self.id, Member.group_id == group_id
            )
        ).first()
        return group.group_admin

    def set_group_admin(self, group_id, set_admin):
        member = (
            db.session.query(Member).filter(
                Member.user_id == self.id, Member.group_id == group_id
            )
        ).first()
        member.group_admin = set_admin

    def has_access_to_object(self, object_id):
        """
        Query filter for objects visible by this user
        """
        if self.has_rights(Capabilities.access_all_objects):
            return True

        return object_id.in_(
            db.session.query(ObjectPermission.object_id).filter(
                self.is_member(ObjectPermission.group_id)
            )
        )

    def workspaces(self):
        """
        Query for workspace groups for this user
        """
        return (
            db.session.query(Group)
            .join(Group.members)
            .join(Member.user)
            .filter(and_(Member.user_id == self.id, Group.workspace.is_(True)))
        )
