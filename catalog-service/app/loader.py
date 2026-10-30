"""Load and validate data/catalog.json at startup. No data fixing happens here:
all cleaning lives in catalog_build/. A file that does not validate stops the service."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from app.domain import Availability, Listing, Occasion, Recipient

SCHEMA_VERSION = 1
PRODUCT_ID = re.compile(r"[A-Z]{2}-\d{3}")


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

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        """Derived fields agree with the fields they are derived from."""
        if not PRODUCT_ID.fullmatch(self.product_id):
            raise ValueError(f"product_id {self.product_id!r} does not match AA-000")
        if not (math.isfinite(self.price_eur) and self.price_eur >= 0):
            raise ValueError(f"{self.product_id}: invalid price_eur {self.price_eur}")
        if not (self.rating is None) == (self.reviews_count is None) == (not self.is_rated):
            raise ValueError(f"{self.product_id}: rating, reviews_count and is_rated disagree")
        if self.rating is not None and not 1 <= self.rating <= 5:
            raise ValueError(f"{self.product_id}: rating {self.rating} outside 1–5")
        if (self.stock == 0) != (self.availability == Availability.out_of_stock):
            raise ValueError(f"{self.product_id}: availability disagrees with stock")
        if self.is_digital != (self.shipping_days == 0):
            raise ValueError(f"{self.product_id}: is_digital disagrees with shipping_days")
        if self.recipient not in self.recipients_match or (
            self.recipient != Recipient.kids and Recipient.kids in self.recipients_match
        ):
            raise ValueError(f"{self.product_id}: recipients_match disagrees with recipient")
        return self


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
    problems = _cross_record_problems(catalog)
    if problems:
        raise CatalogLoadError("catalogue is inconsistent:\n" + "\n".join(problems))
    return catalog


def _cross_record_problems(catalog: CatalogFile) -> list[str]:
    problems = []
    by_id = {p.product_id: p for p in catalog.products}
    id_counts = Counter(p.product_id for p in catalog.products)
    duplicates = sorted(pid for pid, n in id_counts.items() if n > 1)
    if duplicates:
        problems.append(f"duplicate product_id: {duplicates}")

    prefixes: dict[str, set[str]] = {}
    for p in catalog.products:
        prefixes.setdefault(p.category_slug, set()).add(p.product_id[:2])
    for category in catalog.categories:
        if category.slug not in prefixes:
            problems.append(f"category {category.slug} has no products")
        elif len(prefixes[category.slug]) > 1:
            mixed = sorted(prefixes[category.slug])
            problems.append(f"category {category.slug} mixes ID prefixes {mixed}")

    slugs = {c.slug for c in catalog.categories}
    bad_synonyms = sorted(k for k, v in catalog.category_synonyms.items() if v not in slugs)
    if bad_synonyms:
        problems.append(f"category_synonyms point to unknown categories: {bad_synonyms}")

    low_stock_max = catalog.constants.low_stock_max
    for p in catalog.products:
        if p.stock > 0 and (p.availability == Availability.low_stock) != (p.stock <= low_stock_max):
            problems.append(f"{p.product_id}: availability disagrees with stock")
        for listing in p.also_listed_in:
            other = by_id.get(listing.product_id)
            if other is None or other.category_slug != listing.category_slug:
                problems.append(f"{p.product_id}: also_listed_in {listing.product_id} is wrong")
            elif p.product_id not in {o.product_id for o in other.also_listed_in}:
                problems.append(f"{p.product_id}: {listing.product_id} does not list it back")

    groups: dict[str, list[ProductRecord]] = {}
    for p in catalog.products:
        groups.setdefault(p.listing_group, []).append(p)
    for group, members in sorted(groups.items()):
        if [p.product_id for p in members if p.is_primary_listing] != [group]:
            problems.append(f"listing group {group} must have {group} as its only primary")
    return problems
