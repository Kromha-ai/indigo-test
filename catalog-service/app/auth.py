"""X-API-Key authentication.

Applied as a dependency on the data routers only, never as middleware, so the
documentation routes stay public. `APIKeyHeader` declares a security scheme in the
OpenAPI document; the key is never a header *parameter*, which the platform would
show to the LLM as a value to fill in.

A valid key is then counted against its per-minute rate limit. Keys are identified
in logs and in the limiter by their fingerprint, never by their value.
"""

from __future__ import annotations

import hashlib
import secrets

from fastapi import Request, Security
from fastapi.security import APIKeyHeader

from app.errors import CatalogError, unauthorized

api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="ApiKeyAuth",
    auto_error=False,
    description="API key issued by the service operator, sent in the X-API-Key header.",
)


def fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:6]


def require_api_key(request: Request, key: str | None = Security(api_key_header)) -> str:
    valid_keys: tuple[str, ...] = request.app.state.settings.api_keys
    if key is None:
        raise unauthorized()
    # Compare against every key, so timing does not reveal which one nearly matched.
    matched = False
    for valid in valid_keys:
        matched |= secrets.compare_digest(key.encode(), valid.encode())
    if not matched:
        raise unauthorized()

    key_id = fingerprint(key)
    request.state.key_fingerprint = key_id
    retry_after = request.app.state.rate_limiter.hit(key_id)
    if retry_after is not None:
        raise CatalogError(
            "rate_limited",
            "Too many requests for this API key.",
            "Retry after the number of seconds in Retry-After.",
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )
    return key
