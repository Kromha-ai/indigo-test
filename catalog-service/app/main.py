"""App factory. Run with: uv run uvicorn app.main:create_app --factory --env-file .env"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, FastAPI

from app.auth import enforce_rate_limit, require_api_key
from app.catalog import Catalog
from app.errors import ErrorResponse, install_handlers
from app.loader import load_catalog
from app.observability import install_request_logging
from app.ratelimit import RateLimiter
from app.routes import categories, health, products, search
from app.settings import Settings

DESCRIPTION = """\
Product catalogue of an online gift shop, exposed as tools for a gift assistant.

- **search_products**: the default for gift requests defined by recipient, occasion, budget or \
deadline.
- **get_products_by_category**: when the shopper names a kind of product.
- **get_product_details**: for the 2–3 products about to be recommended.
- **get_categories**: what the shop sells, and valid categories and subcategories.

Prices are in EUR. Every data endpoint requires the `X-API-Key` header and is rate-limited \
per key (HTTP 429 with `Retry-After` when exceeded).
"""


def create_app(settings: Settings | None = None, catalog: Catalog | None = None) -> FastAPI:
    if settings is None:
        settings = Settings.from_env()
        logging.basicConfig(level=settings.log_level)
    catalog = catalog or Catalog(load_catalog(settings.data_path))

    app = FastAPI(
        title="Gift Shop Catalog",
        version="0.1.0",
        description=DESCRIPTION,
        servers=[{"url": settings.public_base_url}],
    )
    app.state.settings = settings
    app.state.catalog = catalog
    app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)
    install_handlers(app)
    install_request_logging(app)

    data = APIRouter(
        # In order: reject unknown keys first, then count the request against its key.
        dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)],
        responses={
            401: {"model": ErrorResponse, "description": "Missing or invalid API key."},
            422: {
                "model": ErrorResponse,
                "description": "Invalid parameters; `error.message` names each one.",
            },
            429: {
                "model": ErrorResponse,
                "description": "Rate limit for this API key exceeded; retry after `Retry-After`.",
            },
        },
    )
    data.include_router(categories.router)
    data.include_router(search.router)
    data.include_router(products.router)
    app.include_router(data)
    app.include_router(health.router)
    return app
