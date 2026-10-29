"""Load and validate data/catalog.json at startup. No data fixing happens here:
all cleaning lives in catalog_build/. A file that does not validate stops the service."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from app.domain import Availability, Listing, Occasion, Recipient

SCHEMA_VERSION = 1


class CatalogLoadError(Exception):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProductRecord(_Strict):
    product_id: str
    name: str
    category: str
    category_slug: str
    subcategory: str
    brand: str
    price_eur: float
    stock: int
    availability: Availability
    rating: float | None
    reviews_count: int | None
    is_rated: bool
    rating_score: float
    recipient: Recipient
    recipients_match: list[Recipient]
    occasions: list[Occasion]
    tags: list[str]
    color: str | None
    material: str | None
    gift_wrap: bool
    shipping_days: int
    is_digital: bool
    description: str
    listing_group: str
    is_primary_listing: bool
    also_listed_in: list[Listing]


class CategoryRecord(_Strict):
    slug: str
    name: str


class Constants(_Strict):
    rating_mean: float
    rating_prior_weight: float
    low_stock_max: int


class CatalogFile(_Strict):
    schema_version: int
    constants: Constants
    categories: list[CategoryRecord]
    category_synonyms: dict[str, str]
    products: list[ProductRecord]


def load_catalog(path: Path) -> CatalogFile:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        catalog = CatalogFile.model_validate(raw)
    except FileNotFoundError as error:
        raise CatalogLoadError(f"catalogue file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise CatalogLoadError(f"catalogue file is not valid JSON: {error}") from error
    except ValidationError as error:
        raise CatalogLoadError(
            f"catalogue file does not match the record model:\n{error}"
        ) from error
    if catalog.schema_version != SCHEMA_VERSION:
        raise CatalogLoadError(f"unsupported schema_version {catalog.schema_version}")
    slugs = {c.slug for c in catalog.categories}
    orphans = sorted(p.product_id for p in catalog.products if p.category_slug not in slugs)
    if orphans:
        raise CatalogLoadError(f"products with unknown category: {orphans}")
    if not catalog.products:
        raise CatalogLoadError("catalogue has no products")
    return catalog
