"""Response models. Every field carries a description: the OpenAPI document is read by an LLM.

Optional fields that are absent from a response (e.g. `also_listed_in` on most summaries) are
simply not set; the routes serialize with `response_model_exclude_unset`, so they are omitted
while explicit nulls such as an unrated product's `rating` are kept.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Self

from pydantic import BaseModel, Field

from app.domain import Availability, Listing, Occasion, Recipient
from app.loader import ProductRecord

# --- categories -------------------------------------------------------------------------------


class PriceRange(BaseModel):
    min: float = Field(description="Lowest price in the category, in EUR.")
    max: float = Field(description="Highest price in the category, in EUR.")


class CategoryInfo(BaseModel):
    slug: str = Field(description="Category identifier to use in other calls, e.g. `home-living`.")
    name: str = Field(description="Display name, e.g. `Home & Living`.")
    product_count: int = Field(description="Products in the category, including out of stock.")
    in_stock_count: int = Field(description="Products that can be bought now.")
    price_range_eur: PriceRange = Field(description="Price range of the category, in EUR.")
    subcategories: list[str] = Field(
        description="Subcategories, usable as the `subcategory` filter when browsing."
    )


class CategoriesResponse(BaseModel):
    categories: list[CategoryInfo] = Field(description="All categories of the shop.")


class CategoryRef(BaseModel):
    slug: str = Field(description="Category identifier, e.g. `kitchen-dining`.")
    name: str = Field(description="Display name, e.g. `Kitchen & Dining`.")


# --- products ---------------------------------------------------------------------------------


class _ProductBase(BaseModel):
    """Fields shared by summaries and details. Each declares its own `also_listed_in`."""

    product_id: str = Field(
        description="Product ID, e.g. `HL-003`. Use it with get_product_details."
    )
    name: str = Field(description="Product name.")
    category: str = Field(description="Category slug.")
    subcategory: str = Field(description="Subcategory, e.g. `Candles`.")
    brand: str = Field(description="Brand.")
    price_eur: float = Field(description="Price in EUR.")
    rating: float | None = Field(
        description="Average rating out of 5. `null` means not rated yet, never zero."
    )
    reviews_count: int | None = Field(
        description="Number of reviews behind the rating. `null` when unrated."
    )
    availability: Availability = Field(
        description="`low_stock` means 5 or fewer left: worth mentioning. `out_of_stock` cannot "
        "be bought: never recommend it."
    )
    recipient: Recipient = Field(
        description="Who it suits. `anyone` means any adult; only `kids` products suit children."
    )
    occasions: list[Occasion] = Field(description="Occasions it suits. May be empty.")
    tags: list[str] = Field(description="Descriptive tags, useful to judge style and fit.")
    shipping_days: int = Field(
        description="Working days to deliver. `0` means digital, delivered instantly by email."
    )

    # Summaries carry `also_listed_in` only for cross-listed products; details always do.
    _omit_empty_listings: ClassVar[bool] = False

    @classmethod
    def from_record(cls, record: ProductRecord) -> Self:
        data: dict[str, Any] = record.model_dump(include=set(cls.model_fields) - {"category"})
        data["category"] = record.category_slug
        if cls._omit_empty_listings and not data["also_listed_in"]:
            del data["also_listed_in"]
        return cls(**data)


class ProductSummary(_ProductBase):
    also_listed_in: list[Listing] | None = Field(
        default=None,
        description="Present only when the same product is also listed under another ID in "
        "another category. Never recommend both listings.",
    )

    _omit_empty_listings: ClassVar[bool] = True


class ProductDetail(_ProductBase):
    also_listed_in: list[Listing] = Field(
        description="Other listings of the same product in other categories. Usually empty."
    )
    description: str = Field(
        description="Selling copy. The best source for a recommendation reason."
    )
    color: str | None = Field(description="Colour, if any.")
    material: str | None = Field(description="Materials, if any.")
    gift_wrap: bool = Field(description="Whether gift wrapping is available.")
    is_digital: bool = Field(description="Delivered digitally (by email), instantly.")

    _omit_empty_listings: ClassVar[bool] = False


class ProductDetailResponse(BaseModel):
    found: bool = Field(description="`true`: the product exists. See `product`.")
    product: ProductDetail = Field(description="The full product record.")


# --- lists ------------------------------------------------------------------------------------


class AboveMax(BaseModel):
    count: int = Field(description="Matching products priced above `max_price`.")
    min_price_eur: float = Field(description="Cheapest of them, in EUR.")


class BelowMin(BaseModel):
    count: int = Field(description="Matching products priced below `min_price`.")
    max_price_eur: float = Field(description="Most expensive of them, in EUR.")


class OutsidePriceRange(BaseModel):
    above_max: AboveMax | None = Field(
        default=None, description="Products that match every other filter but cost more."
    )
    below_min: BelowMin | None = Field(
        default=None, description="Products that match every other filter but cost less."
    )


class Suggestion(BaseModel):
    change: str = Field(description="One constraint to relax, in plain words.")
    would_match: int = Field(description="Products that would match after that change.")


class ListResponse(BaseModel):
    found: bool | None = Field(
        default=None,
        description="Browse only: `true` when the category exists. If it does not, the response "
        "is `{found: false, error: {...}}` with `did_you_mean`.",
    )
    category: CategoryRef | None = Field(default=None, description="Browse only: the category.")
    items: list[ProductSummary] = Field(description="This page of products, best match first.")
    total: int = Field(description="Products matching the filters, across all pages.")
    returned: int = Field(description="Products in `items`.")
    offset: int = Field(description="Offset of this page.")
    next_offset: int | None = Field(
        description="Offset of the next page, or `null` on the last page. Prefer narrowing the "
        "filters to paging."
    )
    applied_filters: dict[str, Any] = Field(
        description="The filters as understood, after normalisation (e.g. `Home and Living` → "
        "`home-living`)."
    )
    outside_price_range: OutsidePriceRange | None = Field(
        default=None,
        description="Present when a price filter is set: products matching every other filter "
        "but outside the price band. Tell the shopper about them rather than hiding them.",
    )
    suggestions: list[Suggestion] = Field(
        description="When nothing matches: constraints to relax, best first. Empty otherwise."
    )


# --- operations -------------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = Field(description="`ok` when the catalogue is loaded.")
    products_loaded: int = Field(description="Number of products in memory.")
    catalog_loaded_at: datetime = Field(description="When the catalogue was loaded (UTC).")
