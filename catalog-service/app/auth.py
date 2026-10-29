"""X-API-Key authentication.

Applied as a dependency on the data routers only, never as middleware, so the
documentation routes stay public. `APIKeyHeader` declares a security scheme in the
OpenAPI document; the key is never a header *parameter*, which the platform would
show to the LLM as a value to fill in.
"""

from __future__ import annotations

import secrets

from fastapi import Request, Security
from fastapi.security import APIKeyHeader

from app.errors import unauthorized

api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="ApiKeyAuth",
    auto_error=False,
    description="API key issued by the service operator, sent in the X-API-Key header.",
)


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
    return key
