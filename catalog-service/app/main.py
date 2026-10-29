"""App factory. Run with: uv run uvicorn app.main:create_app --factory --env-file .env"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, FastAPI

from app.auth import require_api_key
from app.catalog import Catalog
from app.errors import ErrorResponse, install_handlers
from app.loader import load_catalog
from app.routes import categories, health
from app.settings import Settings

DESCRIPTION = """\
Product catalogue of an online gift shop, exposed as tools for a gift assistant.

- **search_products**: the default for gift requests defined by recipient, occasion, budget or \
deadline.
- **get_products_by_category**: when the shopper names a kind of product.
- **get_product_details**: for the 2–3 products about to be recommended.
- **get_categories**: what the shop sells, and valid categories and subcategories.

Prices are in EUR. Every data endpoint requires the `X-API-Key` header.
"""


def create_app(settings: Settings | None = None, catalog: Catalog | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
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
    install_handlers(app)

    data = APIRouter(
        dependencies=[Depends(require_api_key)],
        responses={401: {"model": ErrorResponse, "description": "Missing or invalid API key."}},
    )
    data.include_router(categories.router)
    app.include_router(data)
    app.include_router(health.router)
    return app
