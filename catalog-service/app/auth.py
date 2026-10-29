"""X-API-Key authentication and per-key rate limiting.

Both are dependencies on the data routers only, never middleware, so the documentation
routes stay public. `APIKeyHeader` declares a security scheme in the OpenAPI document;
the key is never a header *parameter*, which the platform would show to the LLM as a
value to fill in. Keys are identified in logs and in the limiter by their fingerprint,
never by their value.
"""

from __future__ import annotations

import hashlib
import secrets

from fastapi import Request, Security
from fastapi.security import APIKeyHeader

from app.errors import rate_limited, unauthorized

api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="ApiKeyAuth",
    auto_error=False,
    description="API key issued by the service operator, sent in the X-API-Key header.",
)


def fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:6]


def require_api_key(request: Request, key: str | None = Security(api_key_header)) -> None:
    if key is None:
        raise unauthorized()
    # Compare against every key, so timing does not reveal which one nearly matched.
    matched = False
    for valid in request.app.state.settings.api_keys:
        matched |= secrets.compare_digest(key.encode(), valid.encode())
    if not matched:
        raise unauthorized()
    request.state.key_fingerprint = fingerprint(key)


def enforce_rate_limit(request: Request) -> None:
    """Runs after `require_api_key`, so only valid keys are counted."""
    retry_after = request.app.state.rate_limiter.hit(request.state.key_fingerprint)
    if retry_after is not None:
        raise rate_limited(retry_after)
