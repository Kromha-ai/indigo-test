"""Parameters and response building shared by the list tools."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

from app.catalog import ProductFilter, QueryResult
from app.domain import Occasion, Recipient, SortOrder
from app.errors import invalid_parameter
from app.models import (
    AboveMax,
    BelowMin,
    CategoryRef,
    ListResponse,
    OutsidePriceRange,
    ProductSummary,
)

MAX_LIMIT = 25
DEFAULT_LIMIT = 15


@dataclass(frozen=True)
class ListQuery:
    filter: ProductFilter
    sort: SortOrder
    limit: int
    offset: int


def list_query(
    min_price: float | None = Query(
        None, ge=0, description="Lowest price in EUR, inclusive.", examples=[40]
    ),
    max_price: float | None = Query(
        None,
        ge=0,
        description="Highest price in EUR, inclusive (the shopper's budget).",
        examples=[60],
    ),
    recipient: Recipient | None = Query(
        None,
        description="Who the gift is for. `her`, `him` and `couple` also match products for "
        "`anyone`; `kids` matches only children's products.",
    ),
    occasion: Occasion | None = Query(None, description="The occasion of the gift."),
    max_shipping_days: int | None = Query(
        None,
        ge=0,
        le=14,
        description="Delivery deadline in working days. `0` keeps only instant digital products.",
    ),
    gift_wrap: bool | None = Query(
        None, description="`true` keeps only products that can be gift-wrapped."
    ),
    include_out_of_stock: bool = Query(
        False,
        description="Include products that cannot be bought now, e.g. to answer 'do you have X?'. "
        "Never recommend them.",
    ),
    sort: SortOrder = Query(
        SortOrder.best_rated,
        description="`best_rated` (rating weighted by number of reviews), `price_asc` or "
        "`price_desc`.",
    ),
    limit: int = Query(
        DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description=f"Products per page, at most {MAX_LIMIT}. "
        "Narrow the filters rather than paging.",
    ),
    offset: int = Query(
        0, ge=0, description="Products to skip, for the next page (`next_offset`)."
    ),
) -> ListQuery:
    if min_price is not None and max_price is not None and max_price < min_price:
        raise invalid_parameter(
            f"max_price ({max_price:g}) must be greater than or equal to min_price "
            f"({min_price:g}).",
            "Swap or correct the price bounds and call again.",
        )
    product_filter = ProductFilter(
        min_price=min_price,
        max_price=max_price,
        recipient=recipient,
        occasion=occasion,
        max_shipping_days=max_shipping_days,
        gift_wrap=gift_wrap,
        include_out_of_stock=include_out_of_stock,
    )
    return ListQuery(filter=product_filter, sort=sort, limit=limit, offset=offset)


def _outside_price_range(result: QueryResult) -> OutsidePriceRange:
    outside = OutsidePriceRange()
    if result.prices_above_max:
        outside.above_max = AboveMax(
            count=len(result.prices_above_max), min_price_eur=min(result.prices_above_max)
        )
    if result.prices_below_min:
        outside.below_min = BelowMin(
            count=len(result.prices_below_min), max_price_eur=max(result.prices_below_min)
        )
    return outside


def list_response(
    result: QueryResult,
    query: ListQuery,
    product_filter: ProductFilter,
    category: CategoryRef | None = None,
) -> ListResponse:
    returned = len(result.items)
    end = query.offset + returned
    response = ListResponse(
        items=[ProductSummary.from_record(p) for p in result.items],
        total=result.total,
        returned=returned,
        offset=query.offset,
        next_offset=end if end < result.total else None,
        applied_filters=product_filter.applied(),
        suggestions=[],
    )
    if category is not None:
        response.found = True
        response.category = category
    if product_filter.has_price_band:
        response.outside_price_range = _outside_price_range(result)
    return response
