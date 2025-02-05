from flask import g, request
from sqlalchemy import exists
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import Conflict, Forbidden, InternalServerError, NotFound

from mwdb.core.capabilities import Capabilities
from mwdb.core.config import app_config
from mwdb.core.mail import MailError, send_email_notification
from mwdb.core.plugins import hooks
from mwdb.core.service import Resource
from mwdb.model import Group, Member, User, db
from mwdb.schema.group import (
    GroupCreateRequestSchema,
    GroupInvitationLinkResponseSchema,
    GroupInviteTokenRequestSchema,
    GroupItemResponseSchema,
    GroupListResponseSchema,
    GroupMemberUpdateRequestSchema,
    GroupNameSchemaBase,
    GroupSuccessResponseSchema,
    GroupUpdateRequestSchema,
)
from mwdb.schema.user import UserLoginSchemaBase

from . import (
    load_schema,
    loads_schema,
    logger,
    requires_authorization,
    requires_capabilities,
)


class GroupListResource(Resource):
    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def get(self):
        """
        ---
        summary: List of groups
        description: |
            Returns list of all groups and members.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - group
        responses:
            200:
                description: List of groups
                content:
                  application/json:
                    schema: GroupListResponseSchema
            403:
                description: When user doesn't have `manage_users` capability.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        objs = (
            db.session.query(Group).options(
                joinedload(Group.members), joinedload(Group.members, Member.user)
            )
        ).all()
        schema = GroupListResponseSchema()
        return schema.dump({"groups": objs})


class GroupResource(Resource):
    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def get(self, name):
        """
        ---
        summary: Get group
        description: |
            Returns information about group.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - group
        parameters:
            - in: path
              name: name
              schema:
                type: string
              description: Group name
        responses:
            200:
                description: Group information
                content:
                  application/json:
                    schema: GroupItemResponseSchema
            403:
                description: When user doesn't have `manage_users` capability.
            404:
                description: When group doesn't exist
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        obj = (
            db.session.query(Group)
            .options(joinedload(Group.members), joinedload(Group.members, Member.user))
            .filter(Group.name == name)
        ).first()
        if obj is None:
            raise NotFound("No such group")
        schema = GroupItemResponseSchema()
        return schema.dump(obj)

    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def post(self, name):
        """
        ---
        summary: Create a new group
        description: |
            Creates a new group.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - group
        parameters:
            - in: path
              name: name
              schema:
                type: string
              description: Group name
        requestBody:
            description: Group information
            content:
              application/json:
                schema: GroupCreateRequestSchema
        responses:
            200:
                description: When group was created successfully
                content:
                  application/json:
                    schema: GroupSuccessResponseSchema
            400:
                description: When group name or request body is invalid
            403:
                description: When user doesn't have `manage_users` capability
            409:
                description: When group exists yet
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = GroupCreateRequestSchema()
        obj = loads_schema(request.get_data(as_text=True), schema)

        group_name_obj = load_schema({"name": name}, GroupNameSchemaBase())

        if db.session.query(
            exists().where(Group.name == group_name_obj["name"])
        ).scalar():
            raise Conflict("Group exists yet")

        group = Group(name=group_name_obj["name"], capabilities=obj["capabilities"])
        db.session.add(group)
        db.session.commit()

        hooks.on_created_group(group)
        logger.info(
            "Group created",
            extra={"group": group.name, "capabilities": group.capabilities},
        )
        schema = GroupSuccessResponseSchema()
        return schema.dump({"name": name})

    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def put(self, name):
        """
        ---
        summary: Update group attributes
        description: |
            Updates group attributes.

            If the group is immutable, you can only change capabilities.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - group
        parameters:
            - in: path
              name: name
              schema:
                type: string
              description: Group name
        requestBody:
            description: Group information
            content:
              application/json:
                schema: GroupUpdateRequestSchema
        responses:
            200:
                description: When group was updated successfully
                content:
                  application/json:
                    schema: GroupSuccessResponseSchema
            400:
                description: When group name or request body is invalid
            403:
                description: |
                    When user doesn't have `manage_users` capability
                    or group is immutable
            404:
                description: When group doesn't exist
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = GroupUpdateRequestSchema()
        obj = loads_schema(request.get_data(as_text=True), schema)

        group_name_obj = load_schema({"name": name}, GroupNameSchemaBase())

        group = (
            db.session.query(Group).filter(Group.name == group_name_obj["name"]).first()
        )

        if group is None:
            raise NotFound("No such group")

        immutable_fields = ["name", "default", "workspace"]
        if group.immutable:
            for field in immutable_fields:
                if obj[field] is not None:
                    raise Forbidden(f"Can't change '{field}', group is immutable")

        if obj["name"] is not None:
            group.name = obj["name"]

        if obj["capabilities"] is not None:
            group.capabilities = obj["capabilities"]

        if obj["default"] is not None:
            group.default = obj["default"]

        if obj["workspace"] is not None:
            group.workspace = obj["workspace"]

        db.session.commit()

        hooks.on_updated_group(group)
        logger.info(
            "Group updated",
            extra={"group": group.name, "capabilities": group.capabilities},
        )
        schema = GroupSuccessResponseSchema()
        return schema.dump({"name": group.name})

    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def delete(self, name):
        """
        ---
        summary: Delete group
        description: |
            Remove group from database.

            Requires `manage_users` capability.
        security:
            - bearerAuth: []
        tags:
            - group
        parameters:
            - in: path
              name: name
              schema:
                type: string
              description: Group name
        responses:
            200:
                description: When group was removed successfully
                content:
                  application/json:
                    schema: GroupSuccessResponseSchema
            403:
                description: When user doesn't have `manage_users` capability.
            404:
                description: When group doesn't exist
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        group = (db.session.query(Group).filter(Group.name == name)).first()

        if group is None:
            raise NotFound("No such group")

        if group.immutable is True:
            raise Forbidden(f"Group '{name}' is immutable and can't be removed.")

        db.session.delete(group)
        db.session.commit()

        hooks.on_removed_group(group)
        logger.info("Group was deleted", extra={"group": name})
        schema = GroupSuccessResponseSchema()
        return schema.dump({"name": name})


class GroupMemberResource(Resource):
    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def post(self, name, login):
        """
        ---
        summary: Add a member to the specific group
        description: |
            Adds new member to existing group

            Works only for user-defined groups (excluding private and 'public')

            Requires `manage_users` capability
        security:
            - bearerAuth: []
        tags:
            - group
        parameters:
            - in: path
              name: name
              schema:
                type: string
              description: Group name
            - in: path
              name: login
              schema:
                type: string
              description: Member login
        responses:
            200:
                description: When member was added successfully
                content:
                  application/json:
                    schema: GroupSuccessResponseSchema
            400:
                description: When request body is invalid
            403:
                description: |
                    When user doesn't have `manage_users` capability,
                    group is immutable or user is pending
            404:
                description: When user or group doesn't exist
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        group_name_obj = load_schema({"name": name}, GroupNameSchemaBase())

        user_login_obj = load_schema({"login": login}, UserLoginSchemaBase())

        group = (
            db.session.query(Group)
            .options(joinedload(Group.members), joinedload(Group.members, Member.user))
            .filter(Group.name == group_name_obj["name"])
        ).first()

        if group is None:
            raise NotFound("No such group")

        if group.immutable:
            raise Forbidden("Adding members to immutable group is not allowed")

        member = (
            db.session.query(User).filter(User.login == user_login_obj["login"]).first()
        )
        if member is None:
            raise NotFound("No such user")

        if member.pending:
            raise Forbidden("User is pending and need to be accepted first")

        if not group.add_member(member):
            raise Conflict("Member is already added")
        db.session.commit()

        hooks.on_created_membership(group, member)
        logger.info(
            "Group member added", extra={"user": member.login, "group": group.name}
        )
        schema = GroupSuccessResponseSchema()
        return schema.dump({"name": name})

    @requires_authorization
    @requires_capabilities(Capabilities.manage_users)
    def put(self, name, login):
        """
        ---
        summary: Update group membership
        description: |
            Updates group membership for specific member e.g. to set admin role.

            Works only for user-defined groups (excluding private and 'public')

            Requires `manage_users` capability
        security:
            - bearerAuth: []
        tags:
            - group
        parameters:
            - in: path
              name: name
              schema:
                type: string
              description: Group name
            - in: path
              name: login
              schema:
                type: string
              description: Member login
        requestBody:
            description: Group membership information
            content:
              application/json:
                schema: GroupMemberUpdateRequestSchema
        responses:
            200:
                description: When member was added successfully
                content:
                  application/json:
                    schema: GroupSuccessResponseSchema
            400:
                description: When request body is invalid
            403:
                description: |
                    When user doesn't have `manage_users` capability,
                    group is immutable or user is pending
            404:
                description: When user or group doesn't exist
            409:
                description: When member is already added
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        group_name_obj = load_schema({"name": name}, GroupNameSchemaBase())

        user_login_obj = load_schema({"login": login}, UserLoginSchemaBase())

        membership = loads_schema(
            request.get_data(as_text=True), GroupMemberUpdateRequestSchema()
        )

        group = (
            db.session.query(Group)
            .options(joinedload(Group.members), joinedload(Group.members, Member.user))
            .filter(Group.name == group_name_obj["name"])
        ).first()

        if group is None:
            raise NotFound("No such group")

        if group.immutable:
            raise Forbidden("Change membership in immutable group is not allowed")

        member = (
            db.session.query(User).filter(User.login == user_login_obj["login"]).first()
        )
        if member is None:
            raise NotFound("No such user")

        if member.pending:
            raise Forbidden("User is pending and need to be accepted first")

        member.set_group_admin(group.id, membership["group_admin"])
        db.session.commit()

        hooks.on_updated_membership(group, member)
        logger.info(
            "Group member updated", extra={"user": member.login, "group": group.name}
        )
        schema = GroupSuccessResponseSchema()
        return schema.dump({"name": name})

    @requires_authorization
    def delete(self, name, login):
        """
        ---
        summary: Delete member from group
        description: |
            Removes member from existing group.

            Works only for user-defined groups (excluding private and 'public')

            Requires `manage_users` capability or group_admin membership.
        security:
            - bearerAuth: []
        tags:
            - group
        parameters:
            - in: path
              name: name
              schema:
                type: string
              description: Group name
            - in: path
              name: login
              schema:
                type: string
              description: Member login
        responses:
            200:
                description: When member was removed successfully
                content:
                  application/json:
                    schema: GroupSuccessResponseSchema
            400:
                description: When request body is invalid
            403:
                description: |
                    When user doesn't have `manage_users` capability,
                    group is immutable or user is pending
            404:
                description: When user or group doesn't exist
            409:
                description: When member is already removed
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        group_name_obj = load_schema({"name": name}, GroupNameSchemaBase())
        user_login_obj = load_schema({"login": login}, UserLoginSchemaBase())

        group = (
            db.session.query(Group)
            .options(joinedload(Group.members), joinedload(Group.members, Member.user))
            .filter(Group.name == group_name_obj["name"])
        ).first()
        if not (
            g.auth_user.has_rights(Capabilities.manage_users)
            or g.auth_user.is_group_admin(group.id)
        ):
            raise Forbidden("You are not permitted to manage this group")

        if group is None:
            raise NotFound("No such group")

        if group.immutable:
            raise Forbidden("Removing members from immutable group is not allowed")

        member = (
            db.session.query(User).filter(User.login == user_login_obj["login"]).first()
        )
        if g.auth_user.login == member.login:
            raise Forbidden(
                "You can't remove yourself from the group, "
                "only system admin can remove group admins."
            )
        if member is None:
            raise NotFound("No such user")

        if member.pending:
            raise Forbidden("User is pending and need to be accepted first")

        if not group.remove_member(member):
            raise Conflict("Member is already removed")
        db.session.commit()

        hooks.on_removed_membership(group, member)
        logger.info(
            "Group member deleted", extra={"user": member.login, "group": group.name}
        )
        schema = GroupSuccessResponseSchema()
        return schema.dump({"name": name})


@rate_limited_resource
class GroupInviteResource(Resource):
    @requires_authorization
    def post(self, name, invited_user):
        """
        ---
        summary: Request invitation link
        description: |
            Creates invitation link and sends an email to the invited user.

            Invitation link works only for secified group and specified user

            Requires `manage_users` capability or group_admin membership.
        security:
            - bearerAuth: []
        tags:
            - group
        parameters:
            - in: path
              name: name
              schema:
                type: string
              description: Group name
            - in: path
              name: invited_user
              schema:
                type: string
              description: Invited user login
        responses:
            200:
                description: When link was created successfully
                content:
                  application/json:
                    schema: GroupInvitationLinkResponseSchema
            400:
                description: When request body is invalid
            403:
                description: |
                    When user doesn't have enough permissions,
                    group is immutable or invited user is pending
            404:
                description: When invited user or group doesn't exist
            409:
                description: When user is already a member of this group
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        group_obj = (db.session.query(Group).filter(Group.name == name)).first()

        if group_obj is None:
            raise NotFound("Group does not exist or you are not its member")

        member_obj = (
            db.session.query(Member)
            .filter(Member.group_id == group_obj.id)
            .filter(Member.user_id == g.auth_user.id)
        ).first()

        if member_obj is None:
            raise NotFound("Group does not exist or you are not its member")

        if not member_obj.group_admin:
            raise Forbidden("You do not have group_admin role")

        if group_obj.private or group_obj.immutable:
            raise Forbidden("You cannot invite users to this group")

        invited_user_obj = (
            db.session.query(User).filter(User.login == invited_user)
        ).first()

        if invited_user_obj is None:
            raise NotFound("Invited user does not exist")

        if invited_user_obj.pending:
            raise Forbidden("Invited user is pending")

        if (
            db.session.query(Member)
            .filter(Member.group_id == group_obj.id)
            .filter(Member.user_id == invited_user_obj.id)
        ).first() is not None:
            raise Conflict("Invited user is already a member of this group")

        token = invited_user_obj.generate_group_invite_token(
            group_obj.id, app_config.mwdb.group_invite_expiration_time
        )

        try:
            send_email_notification(
                "group_invitation",
                "You have been invited to a new group in MWDB",
                invited_user_obj.email,
                base_url=app_config.mwdb.base_url,
                login=invited_user_obj.login,
                group_invite_token=token,
            )
        except MailError:
            logger.exception("Can't send e-mail notification")
            raise InternalServerError(
                "SMTP server needed to fulfill this request is"
                " not configured or unavailable."
            )

        schema = GroupInvitationLinkResponseSchema()
        return schema.dump(
            {"link": app_config.mwdb.base_url + "/group/invite?token=" + token}
        )


@rate_limited_resource
class GroupJoinResource(Resource):
    @requires_authorization
    def get(self):
        """
        ---
        summary: Get information about group from invitation token
        description: |
            Get information about group from invitation token

        security:
            - bearerAuth: []
        parameters:
            - in: query
              name: token
              schema:
                type: string
              description: token
        tags:
            - group
        responses:
            200:
                description: When data was read successfully
                content:
                  application/json:
                    schema: GroupSuccessResponseSchema
            400:
                description: When request body is invalid
            403:
                description: When there was a problem with the token
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        args = load_schema(request.args, GroupInviteTokenRequestSchema())
        token_data = User.verify_group_invite_token(args["token"])
        if not token_data:
            raise Forbidden(
                "Token expired, please re-request invitation to the group administrator"
            )

        invited_user, group_id = token_data
        if g.auth_user.id != invited_user.id:
            raise Forbidden("This invitation is not for you")

        group_obj = db.session.query(Group).filter(Group.id == group_id).first()
        if group_obj is None:
            raise NotFound("Group does not exist")

        schema = GroupSuccessResponseSchema()
        return schema.dump({"name": group_obj.name})

    @requires_authorization
    def post(selt):
        """
        ---
        summary: Join group using invitation link
        description: |
            Join group using link

        security:
            - bearerAuth: []
        parameters:
            - in: query
              name: token
              schema:
                type: string
              description: token
        tags:
            - group
        responses:
            200:
                description: When user joined group successfully
                content:
                  application/json:
                    schema: GroupSuccessResponseSchema
            400:
                description: When request body is invalid
            403:
                description: When there was a problem with the token
            409:
                description: When user is already a member of this group
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        args = load_schema(request.args, GroupInviteTokenRequestSchema())
        token_data = User.verify_group_invite_token(args["token"])
        if not token_data:
            raise Forbidden(
                "Token expired, please re-request invitation to the group administrator"
            )

        invited_user, group_id = token_data
        if g.auth_user.id != invited_user.id:
            raise Forbidden("This invitation is not for you")

        member = (
            db.session.query(Member)
            .filter(Member.group_id == group_id)
            .filter(Member.user_id == g.auth_user.id)
        ).first()

        if member is not None:
            raise Conflict("You are already member of this group")

        group_obj = db.session.query(Group).filter(Group.id == group_id).first()
        if group_obj is None:
            raise NotFound("This group does not exist")

        group_obj.add_member(g.auth_user)
        db.session.commit()

        schema = GroupSuccessResponseSchema()
        return schema.dump({"name": group_obj.name})
