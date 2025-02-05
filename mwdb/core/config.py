import os
from enum import Enum
from typing import List

from typedconfig import Config, group_key, key, section
from typedconfig.source import EnvironmentConfigSource, IniFileConfigSource

from mwdb.paths import mail_templates_dir


def intbool(v: str) -> bool:
    return bool(int(v))


def list_of_str(v: str) -> List[str]:
    return [el.strip() for el in v.split(",") if el.strip()]


def path(v: str) -> str:
    if not v:
        raise ValueError("Path can't be empty")
    v = os.path.abspath(v)
    if not os.path.exists(v):
        raise ValueError(f"Path {v} doesn't exist")
    return v


class StorageProviderType(Enum):
    DISK = "DISK"
    S3 = "S3"


def storage_provider_from_str(v: str) -> StorageProviderType:
    if not v:
        return StorageProviderType.DISK

    v = v.upper()
    try:
        return StorageProviderType[v]
    except KeyError:
        raise ValueError(f"Storage provider {v} doesn't exist")


@section("mwdb")
class MWDBConfig(Config):
    # PostgreSQL database URI
    postgres_uri = key(cast=str, required=True)
    # PostgreSQL database statement_timeout parameter
    statement_timeout = key(cast=int, required=False, default=0)
    # Flask secret key
    secret_key = key(cast=str, required=True)
    # Redis database URI
    redis_uri = key(cast=str, required=False, default=None)
    # Serve web application
    serve_web = key(cast=intbool, required=False, default=True)
    # Folder with web application files
    # (if not set: served from pre-built package bundle)
    web_folder = key(cast=path, required=False, default=None)
    # Base application URL, accessible for users
    base_url = key(cast=str, required=False, default="http://127.0.0.1")
    # MWDB local instance name
    instance_name = key(cast=str, required=False, default="mwdb")
    # Flask additional settings file (optional)
    flask_config_file = key(cast=path, required=False)
    # Axios request timeout
    request_timeout = key(cast=int, required=False, default=20000)
    # Which storage provider to use (options: disk or s3)
    storage_provider = key(
        cast=storage_provider_from_str, required=False, default=StorageProviderType.DISK
    )
    # File upload timeout
    file_upload_timeout = key(cast=int, required=False, default=60000)
    # Maximum upload size, default is None (no limit)
    # This value refers to whole upload request ('Content-Length' from request header)
    # Maximum file size is smaller than that by +/- 500 B
    max_upload_size = key(cast=int, required=False, default=None)
    # Folder for uploads
    uploads_folder = key(cast=path, required=False)
    # Should we break up the uploads into different folders for example:
    # uploads/9/f/8/6/9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
    hash_pathing = key(cast=intbool, required=False, default=True)
    # Try to open file using opposite hash_pathing setting when MWDB
    # fails to open file using current one. It's useful when you want to
    # migrate from one scheme to another.
    hash_pathing_fallback = key(cast=intbool, required=False, default=False)
    # S3 compatible storage endpoint
    s3_storage_endpoint = key(cast=str, required=False)
    # Use TLS with S3 storage
    s3_storage_secure = key(cast=intbool, required=False, default=False)
    # S3 storage Access Key
    s3_storage_access_key = key(cast=str, required=False)
    # S3 storage Secret Key
    s3_storage_secret_key = key(cast=str, required=False)
    # S3 storage Region Name (For example, 'us-east-1')
    s3_storage_region_name = key(cast=str, required=False)
    # S3 storage Bucket Name
    s3_storage_bucket_name = key(cast=str, required=False)
    # S3 storage Authorize through IAM role (No credentials)
    s3_storage_iam_auth = key(cast=intbool, required=False)
    # Limit number of objects returned by listing endpoints
    listing_endpoints_count_limit = key(cast=int, required=False, default=1000)

    # Administrator account login
    admin_login = key(cast=str, required=False, default="admin")
    # Administrator account first password
    admin_password = key(cast=str, required=False)

    enable_plugins = key(cast=intbool, required=False, default=True)
    # List of plugin names to be loaded, separated by commas
    plugins = key(cast=list_of_str, required=False, default=[])
    # Directory that will be added to sys.path for plugin imports
    # Allows to load local plugins without installing them in site-packages
    local_plugins_folder = key(cast=path, required=False, default=None)
    # Auto-discover plugins contained in local_plugins_folder
    local_plugins_autodiscover = key(cast=intbool, required=False, default=False)

    remotes = key(cast=list_of_str, required=False, default=[])

    enable_rate_limit = key(cast=intbool, required=False, default=False)
    enable_registration = key(cast=intbool, required=False, default=False)
    enable_maintenance = key(cast=intbool, required=False, default=False)
    enable_hooks = key(cast=intbool, required=False, default=True)
    enable_karton = key(cast=intbool, required=False, default=False)
    enable_oidc = key(cast=intbool, required=False, default=False)
    enable_3rd_party_sharing_consent = key(cast=intbool, required=False, default=False)

    mail_smtp = key(cast=str, required=False)
    mail_from = key(cast=str, required=False, default="noreply@mwdb")
    mail_templates_folder = key(cast=path, required=False, default=mail_templates_dir)
    mail_username = key(cast=str, required=False)
    mail_password = key(cast=str, required=False)
    mail_tls = key(cast=intbool, required=False, default=False)

    recaptcha_site_key = key(cast=str, required=False)
    recaptcha_secret = key(cast=str, required=False)

    enable_json_logger = key(cast=intbool, required=False, default=False)
    enable_sql_profiler = key(cast=intbool, required=False, default=False)
    enable_prometheus_metrics = key(cast=intbool, required=False, default=False)
    log_only_slow_sql = key(cast=intbool, required=False, default=False)
    use_x_forwarded_for = key(cast=intbool, required=False, default=False)
    enable_debug_log = key(cast=intbool, required=False, default=False)
    enable_brownout = key(cast=intbool, required=False, default=False)

    group_invite_expiration_time = key(
        cast=int, required=False, default=7 * 24 * 3600
    )  # one week


@section("karton")
class KartonConfig(Config):
    config_path = key(cast=str, required=False, default=None)


@section("mwdb_limiter")
class MWDBLimiterConfig(Config):
    # Section keys are read dynamically (<resourcename>_<method>)
    pass


class AppConfig(Config):
    mwdb = group_key(MWDBConfig)
    karton = group_key(KartonConfig)
    mwdb_limiter = group_key(MWDBLimiterConfig)


def _config_sources():
    return [
        EnvironmentConfigSource(),
        IniFileConfigSource("mwdb.ini", must_exist=False),
        IniFileConfigSource(
            os.path.expanduser("~/.mwdb-core/mwdb.ini"), must_exist=False
        ),
        IniFileConfigSource("/etc/mwdb-core/mwdb.ini", must_exist=False),
    ]


app_config = AppConfig(sources=_config_sources())


def reload_config():
    app_config.provider.set_sources(_config_sources())
    app_config.provider.clear_cache()
