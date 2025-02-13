import datetime
from enum import Enum
from typing import Any

import jwt

from mwdb.core.config import app_config


class AuthScope(Enum):
    session = "session"
    api_key = "api_key"
    set_password = "set_password"
    download_file = "download_file"


def generate_token(fields, scope, expiration=None):
    issued_at = datetime.datetime.now(tz=datetime.timezone.utc)
    token_claims = {
        **fields,
        "iat": issued_at,
        "aud": app_config.mwdb.base_url,
        "scope": scope.value,
    }

    if "login" in fields.keys():
        token_claims["sub"] = fields["login"]
    if expiration is not None:
        token_claims["exp"] = issued_at + datetime.timedelta(seconds=expiration)
    payload = {**fields, **token_claims}
    token = jwt.encode(payload, app_config.mwdb.secret_key, algorithm="HS512")
    return token


def verify_token(token: str, scope: AuthScope) -> Any:
    try:
        data = jwt.decode(
            token,
            key=app_config.mwdb.secret_key,
            algorithms=["HS512"],
            audience=app_config.mwdb.base_url,
            options={"verify_aud": True},
        )
        if data.get("scope") != scope.value:
            return None

        if scope.value != "download_file" and "sub" not in data:
            return None

    except jwt.InvalidTokenError:
        return None
    return data


def verify_legacy_api_key(token: str) -> Any:
    try:
        data = jwt.decode(
            token,
            key=app_config.mwdb.secret_key,
            algorithms=["HS512"],
        )
        if set(data.keys()) != {"login", "api_key_id"}:
            return None

    except jwt.InvalidTokenError:
        return None
    return data
