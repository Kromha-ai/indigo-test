"""Response models. Every field carries a description: the OpenAPI document is read by an LLM."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


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
    in_stock_by_occasion: dict[str, int] = Field(
        description='In-stock products per occasion, e.g. `{"housewarming": 18}`. Shows which '
        "categories hold gifts for an occasion."
    )


class CategoriesResponse(BaseModel):
    categories: list[CategoryInfo] = Field(description="All categories of the shop.")


class HealthResponse(BaseModel):
    status: str = Field(description="`ok` when the catalogue is loaded.")
    products_loaded: int = Field(description="Number of products in memory.")
    catalog_loaded_at: datetime = Field(description="When the catalogue was loaded (UTC).")
