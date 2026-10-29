from dataclasses import replace

from fastapi import APIRouter, Depends, Query, Request

from app.catalog import RELAXABLE, Catalog
from app.models import ListResponse
from app.routes.listing import ListQuery, list_query, list_response, require_category

router = APIRouter(tags=["catalogue"])


@router.get(
    "/products/search",
    operation_id="search_products",
    summary="Find gift ideas across the shop by constraints",
    description=(
        "Find gift ideas across the whole shop by the shopper's constraints: who it is for "
        "(recipient), the occasion, a budget (min_price / max_price), a delivery deadline "
        "(max_shipping_days), gift wrap. This is the default tool for gift requests ('something "
        "for my sister's new flat, about €50'). There is no free-text search: moods and tastes "
        "('cosy', 'she loves music') are for you to judge from the returned names, tags and "
        "subcategories. Returns up to 15 compact summaries, best rated first, one per product; "
        "narrow the filters rather than paging. 'outside_price_range' tells you when matching "
        "products exist just outside the budget. If nothing matches, 'suggestions' says which "
        "constraint to relax. Call get_product_details on the 2–3 you intend to recommend. "
        "With no filters at all it returns the shop's best-rated products."
    ),
    response_model=ListResponse,
    response_model_exclude_unset=True,
)
def search_products(
    request: Request,
    category: str | None = Query(
        None,
        description="Optional: limit the search to one category (slug or display name). Leave "
        "it out to search the whole shop, which is usually what you want.",
        examples=["home-living"],
    ),
    query: ListQuery = Depends(list_query),
) -> ListResponse:
    catalog: Catalog = request.app.state.catalog
    slug = require_category(catalog, category) if category is not None else None
    product_filter = replace(query.filter, category=slug, primary_only=True)
    result = catalog.query(
        product_filter, query.sort, query.limit, query.offset, relaxable=(*RELAXABLE, "category")
    )
    request.state.result_count = result.total
    return list_response(result, query, product_filter)
