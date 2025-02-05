import os
from datetime import datetime

from flask import g, request
from flask_migrate import Migrate
from werkzeug.exceptions import Forbidden
from werkzeug.routing import BaseConverter

from mwdb.core.app import api, app
from mwdb.core.config import app_config
from mwdb.core.deprecated import DeprecatedFeature, uses_deprecated_api
from mwdb.core.log import getLogger, setup_logger
from mwdb.core.metrics import metric_api_requests, metrics_enabled
from mwdb.core.plugins import PluginAppContext, load_plugins
from mwdb.core.rate_limit import apply_rate_limit_for_request
from mwdb.core.static import static_blueprint
from mwdb.core.util import token_hex
from mwdb.model import APIKey, User, db
from mwdb.paths import migrations_dir
from mwdb.resources.api_key import APIKeyIssueResource, APIKeyResource
from mwdb.resources.attribute import (
    AttributeDefinitionListResource,
    AttributeDefinitionResource,
    AttributeListResource,
    AttributePermissionResource,
    AttributeResource,
)
from mwdb.resources.auth import (
    AuthGroupListResource,
    ChangePasswordResource,
    LoginResource,
    RecoverPasswordResource,
    RefreshTokenResource,
    RegisterResource,
    RequestPasswordChangeResource,
    ValidateTokenResource,
)
from mwdb.resources.blob import TextBlobItemResource, TextBlobResource
from mwdb.resources.comment import CommentDeleteResource, CommentResource
from mwdb.resources.config import (
    ConfigItemResource,
    ConfigResource,
    ConfigStatsResource,
)
from mwdb.resources.download import DownloadResource, RequestSampleDownloadResource
from mwdb.resources.file import (
    FileDownloadResource,
    FileDownloadZipResource,
    FileItemResource,
    FileResource,
)
from mwdb.resources.group import (
    GroupInviteResource,
    GroupJoinResource,
    GroupListResource,
    GroupMemberResource,
    GroupResource,
)
from mwdb.resources.karton import KartonAnalysisResource, KartonObjectResource
from mwdb.resources.metakey import (
    MetakeyDefinitionManageResource,
    MetakeyListDefinitionManageResource,
    MetakeyListDefinitionResource,
    MetakeyPermissionResource,
    MetakeyResource,
)
from mwdb.resources.metrics import MetricsResource
from mwdb.resources.oauth import (
    OpenIDAccountIdentitiesResource,
    OpenIDAuthenticateResource,
    OpenIDAuthorizeResource,
    OpenIDBindAccountResource,
    OpenIDLogoutResource,
    OpenIDProviderResource,
    OpenIDRegisterUserResource,
    OpenIDSingleProviderResource,
)
from mwdb.resources.object import (
    ObjectCountResource,
    ObjectFavoriteResource,
    ObjectItemResource,
    ObjectResource,
    ObjectShare3rdPartyResource,
)
from mwdb.resources.quick_query import QuickQueryItemResource, QuickQueryResource
from mwdb.resources.relations import ObjectChildResource, RelationsResource
from mwdb.resources.remotes import (
    RemoteAPIResource,
    RemoteConfigPullResource,
    RemoteConfigPushResource,
    RemoteFilePullResource,
    RemoteFilePushResource,
    RemoteListResource,
    RemoteTextBlobPullResource,
    RemoteTextBlobPushResource,
)
from mwdb.resources.search import SearchResource
from mwdb.resources.server import (
    PingResource,
    ServerAdminInfoResource,
    ServerDocsResource,
    ServerInfoResource,
)
from mwdb.resources.share import ShareGroupListResource, ShareResource
from mwdb.resources.tag import TagListResource, TagResource
from mwdb.resources.user import (
    UserGetPasswordChangeTokenResource,
    UserListResource,
    UserPendingResource,
    UserProfileResource,
    UserRequestPasswordChangeResource,
    UserResource,
)


class HashConverter(BaseConverter):
    # MD5/SHA1/SHA256/SHA512 (32,40,64,128)
    regex = "root|[A-Fa-f0-9]{32,128}"


app.config["SQLALCHEMY_DATABASE_URI"] = app_config.mwdb.postgres_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = app_config.mwdb.secret_key
"""
Flask-restful tries to be smart and transforms NotFound exceptions.
Adds: "You have requested this URI [/file/root] but did you mean
/file/<string:identifier> or /file ?" even if URI is completely correct,
but some objects needed to fulfill request are missing.
"""
app.config["ERROR_404_HELP"] = False

# Load Flask-specific overrides if specified
if app_config.mwdb.flask_config_file:
    app.config.from_pyfile(app_config.mwdb.flask_config_file)

app.url_map.converters["hash64"] = HashConverter

migrate = Migrate(app, db, directory=migrations_dir, compare_type=True)
db.init_app(app)

if app_config.mwdb.serve_web:
    app.register_blueprint(static_blueprint)


@api.blueprint.before_request
def assign_request_id():
    g.request_id = token_hex(16)
    g.request_start_time = datetime.utcnow()
    getLogger().debug(
        "before_request",
        extra={
            "path": request.path,
            "arguments": request.args,
            "method": request.method,
            "remote_addr": request.remote_addr,
            "pid": os.getpid(),
        },
    )


@api.blueprint.after_request
def log_request(response):
    if hasattr(g, "request_start_time"):
        response_time = datetime.utcnow() - g.request_start_time
    else:
        response_time = None
    response_size = response.calculate_content_length()

    if metrics_enabled():
        user = g.auth_user.login if g.auth_user else request.remote_addr
        metric_api_requests.inc(
            method=request.method,
            endpoint=request.endpoint,
            user=str(user),
            status_code=str(response.status_code),
        )

    getLogger().debug(
        "request",
        extra={
            "path": request.path,
            "arguments": request.args,
            "method": request.method,
            "status": response.status_code,
            "response_time": response_time,
            "response_size": response_size,
            "remote_addr": request.remote_addr,
            "pid": os.getpid(),
        },
    )

    return response


@api.blueprint.before_request
def require_auth():
    if request.method == "OPTIONS":
        return

    auth = request.headers.get("Authorization")

    g.auth_user = None
    g.auth_provider = None

    if auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        result = User.verify_session_token(token)
        if result is not None:
            g.auth_user, g.auth_provider = result
        # Not a session token? Maybe APIKey token
        if g.auth_user is None:
            g.auth_user = APIKey.verify_token(token)
        # Still nothing? Maybe legacy API key
        if g.auth_user is None:
            g.auth_user = User.verify_legacy_token(token)
            if g.auth_user is not None:
                uses_deprecated_api(DeprecatedFeature.legacy_api_key_v1)

    if g.auth_user:
        if (
            app_config.mwdb.enable_maintenance
            and g.auth_user.login != app_config.mwdb.admin_login
        ):
            raise Forbidden("Maintenance underway. Please come back later.")

        if g.auth_user.disabled:
            raise Forbidden("User has been disabled.")


@api.blueprint.before_request
def apply_rate_limit():
    apply_rate_limit_for_request()


# Server health endpoints
api.add_resource(PingResource, "/ping")
api.add_resource(ServerInfoResource, "/server")
api.add_resource(ServerAdminInfoResource, "/server/admin")
api.add_resource(ServerDocsResource, "/docs")

# Authentication endpoints
api.add_resource(LoginResource, "/auth/login")
api.add_resource(ChangePasswordResource, "/auth/change_password")
api.add_resource(RecoverPasswordResource, "/auth/recover_password")
api.add_resource(RequestPasswordChangeResource, "/auth/request_password_change")
api.add_resource(RefreshTokenResource, "/auth/refresh")
api.add_resource(ValidateTokenResource, "/auth/validate")
api.add_resource(AuthGroupListResource, "/auth/groups")
api.add_resource(RegisterResource, "/auth/register")

# API key endpoints
api.add_resource(APIKeyIssueResource, "/user/<login>/api_key")
api.add_resource(APIKeyResource, "/api_key/<api_key_id>")

# Object endpoints
api.add_resource(ObjectResource, "/object")
api.add_resource(ObjectItemResource, "/object/<hash64:identifier>")
api.add_resource(ObjectFavoriteResource, "/object/<hash64:identifier>/favorite")

if app_config.mwdb.enable_3rd_party_sharing_consent:
    api.add_resource(
        ObjectShare3rdPartyResource, "/object/<hash64:identifier>/share_3rd_party"
    )

# Count endpoint
api.add_resource(ObjectCountResource, "/<any(file, config, blob, object):type>/count")

# Tag endpoints
api.add_resource(TagListResource, "/tag")
api.add_resource(
    TagResource, "/<any(file, config, blob, object):type>/<hash64:identifier>/tag"
)

# Comment endpoints
api.add_resource(
    CommentResource,
    "/<any(file, config, blob, object):type>/" "<hash64:identifier>/comment",
)
api.add_resource(
    CommentDeleteResource,
    "/<any(file, config, blob, object):type>/"
    "<hash64:identifier>/comment/<int:comment_id>",
)

# Share endpoints
api.add_resource(
    ShareResource, "/<any(file, config, blob, object):type>/<hash64:identifier>/share"
)
api.add_resource(ShareGroupListResource, "/share")

# Relation endpoints
api.add_resource(
    RelationsResource,
    "/<any(file, config, blob, object):type>/<hash64:identifier>/relations",
)
api.add_resource(
    ObjectChildResource,
    "/<any(file, config, blob, object):type>/<hash64:parent>/child/<hash64:child>",
)

# File endpoints
api.add_resource(FileResource, "/file")
api.add_resource(FileItemResource, "/file/<hash64:identifier>")
api.add_resource(FileDownloadResource, "/file/<hash64:identifier>/download")
api.add_resource(FileDownloadZipResource, "/file/<hash64:identifier>/download/zip")

# Config endpoints
api.add_resource(ConfigResource, "/config")
api.add_resource(ConfigStatsResource, "/config/stats")
api.add_resource(ConfigItemResource, "/config/<hash64:identifier>")

# Blob endpoints
api.add_resource(TextBlobResource, "/blob")
api.add_resource(TextBlobItemResource, "/blob/<hash64:identifier>")

# Download endpoints
api.add_resource(RequestSampleDownloadResource, "/request/sample/<identifier>")
api.add_resource(DownloadResource, "/download/<access_token>")

# Search endpoints
api.add_resource(SearchResource, "/search")

# Quick query endpoints
api.add_resource(
    QuickQueryResource, "/<any(file, config, blob, object):type>/quick_query"
)
api.add_resource(QuickQueryItemResource, "/quick_query/<int:id>")

# Attribute endpoints
api.add_resource(
    AttributeListResource,
    "/<any(file, config, blob, object):type>/<hash64:identifier>/attribute",
)
api.add_resource(
    AttributeResource,
    "/<any(file, config, blob, object):type>/<hash64:identifier>"
    "/attribute/<int:attribute_id>",
)
api.add_resource(AttributeDefinitionListResource, "/attribute")
api.add_resource(AttributeDefinitionResource, "/attribute/<key>")
api.add_resource(AttributePermissionResource, "/attribute/<key>/permissions")

# Attribute (metakey) deprecated endpoints
api.add_resource(MetakeyListDefinitionResource, "/meta/list/<any(read, set):access>")
api.add_resource(
    MetakeyResource, "/<any(file, config, blob, object):type>/<hash64:identifier>/meta"
)
api.add_resource(MetakeyListDefinitionManageResource, "/meta/manage")
api.add_resource(MetakeyDefinitionManageResource, "/meta/manage/<key>")
api.add_resource(
    MetakeyPermissionResource, "/meta/manage/<key>/permissions/<group_name>"
)

# Karton endpoints
api.add_resource(
    KartonObjectResource,
    "/<any(file, config, blob, object):type>/<hash64:identifier>/karton",
)
api.add_resource(
    KartonAnalysisResource,
    "/<any(file, config, blob, object):type>/<hash64:identifier>/karton/<analysis_id>",
)

# User endpoints
api.add_resource(UserListResource, "/user")
api.add_resource(UserResource, "/user/<login>")
api.add_resource(UserProfileResource, "/profile/<login>")
api.add_resource(
    UserRequestPasswordChangeResource, "/user/<login>/request_password_change"
)
api.add_resource(UserGetPasswordChangeTokenResource, "/user/<login>/change_password")
api.add_resource(UserPendingResource, "/user/<login>/pending")

# Group endpoints
api.add_resource(GroupListResource, "/group")
api.add_resource(GroupResource, "/group/<name>")
api.add_resource(GroupMemberResource, "/group/<name>/member/<login>")
api.add_resource(GroupInviteResource, "/group/<name>/invite/<invited_user>")
api.add_resource(GroupJoinResource, "/group/join")

# OAuth endpoints
if app_config.mwdb.enable_oidc:
    api.add_resource(OpenIDProviderResource, "/oauth")
    api.add_resource(OpenIDAccountIdentitiesResource, "/oauth/identities")
    api.add_resource(OpenIDSingleProviderResource, "/oauth/<provider_name>")
    api.add_resource(OpenIDAuthenticateResource, "/oauth/<provider_name>/authenticate")
    api.add_resource(OpenIDAuthorizeResource, "/oauth/<provider_name>/authorize")
    api.add_resource(OpenIDBindAccountResource, "/oauth/<provider_name>/bind_account")
    api.add_resource(OpenIDRegisterUserResource, "/oauth/<provider_name>/register")
    api.add_resource(OpenIDLogoutResource, "/oauth/<provider_name>/logout")

# Remote endpoints
api.add_resource(RemoteListResource, "/remote")
api.add_resource(RemoteAPIResource, "/remote/<remote_name>/api/<path:remote_path>")
api.add_resource(
    RemoteFilePullResource, "/remote/<remote_name>/pull/file/<hash64:identifier>"
)
api.add_resource(
    RemoteConfigPullResource, "/remote/<remote_name>/pull/config/<hash64:identifier>"
)
api.add_resource(
    RemoteTextBlobPullResource, "/remote/<remote_name>/pull/blob/<hash64:identifier>"
)
api.add_resource(
    RemoteFilePushResource, "/remote/<remote_name>/push/file/<hash64:identifier>"
)
api.add_resource(
    RemoteConfigPushResource, "/remote/<remote_name>/push/config/<hash64:identifier>"
)
api.add_resource(
    RemoteTextBlobPushResource, "/remote/<remote_name>/push/blob/<hash64:identifier>"
)

if metrics_enabled():
    api.add_resource(MetricsResource, "/varz")

setup_logger()

# Load plugins
plugin_context = PluginAppContext()
with app.app_context():
    load_plugins(plugin_context)

# Register blueprint
api.register()
