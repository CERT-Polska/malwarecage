"""
Utilities for marking deprecated features to monitor usage
"""
from enum import Enum
from functools import wraps
from typing import Optional

from flask import g, request
from werkzeug.exceptions import BadRequest

from mwdb.core.config import app_config
from mwdb.core.log import getLogger
from mwdb.core.metrics import metric_deprecated_usage

logger = getLogger()


class DeprecatedFeature(Enum):
    # API keys non-complaint with RFC7519
    # Deprecated in v2.7.0
    legacy_api_key_v2 = "legacy_api_key_v2"


def uses_deprecated_api(
    feature: DeprecatedFeature,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    user: Optional[str] = None,
):
    if user is None:
        user = g.auth_user.login if g.auth_user is not None else None
    metric_deprecated_usage.inc(
        feature=str(feature.value), endpoint=endpoint, method=method, user=user
    )
    logger.debug(
        f"Used deprecated feature: {feature}"
        + (f" ({method} {endpoint})" if endpoint is not None else "")
    )
    if app_config.mwdb.enable_brownout:
        if feature == DeprecatedFeature.legacy_api_key_v2:
            # This feature won't be removed in v3
            return
        raise BadRequest(
            f"Brownout: {feature} API feature is deprecated and currently disabled. "
            f"Please upgrade your MWDB API client."
        )


def deprecated_endpoint(feature: DeprecatedFeature):
    def method_wrapper(f):
        @wraps(f)
        def endpoint(*args, **kwargs):
            uses_deprecated_api(
                feature, endpoint=request.endpoint, method=request.method
            )
            return f(*args, **kwargs)

        return endpoint

    return method_wrapper
