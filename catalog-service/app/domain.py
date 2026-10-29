"""Vocabulary shared by the catalogue file, the queries and the API: one definition each."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Recipient(StrEnum):
    her = "her"
    him = "him"
    couple = "couple"
    kids = "kids"
    anyone = "anyone"


class Occasion(StrEnum):
    birthday = "birthday"
    thank_you = "thank-you"
    christmas = "christmas"
    housewarming = "housewarming"
    anniversary = "anniversary"
    graduation = "graduation"


class Availability(StrEnum):
    in_stock = "in_stock"
    low_stock = "low_stock"
    out_of_stock = "out_of_stock"


class SortOrder(StrEnum):
    best_rated = "best_rated"
    price_asc = "price_asc"
    price_desc = "price_desc"


class Listing(BaseModel):
    """Another listing of the same product, under another ID in another category."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    product_id: str = Field(description="ID of the other listing of the same product.")
    category_slug: str = Field(description="Category where that other listing appears.")
