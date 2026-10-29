from dataclasses import replace

from fastapi import APIRouter, Depends, Path, Query, Request

from app.catalog import Catalog
from app.errors import category_not_found, subcategory_not_found
from app.models import CategoriesResponse, CategoryRef, ListResponse
from app.routes.listing import ListQuery, list_query, list_response

router = APIRouter(tags=["catalogue"])


@router.get(
    "/categories",
    operation_id="get_categories",
    summary="List the shop's categories",
    description=(
        "List the shop's 11 categories with product counts, price ranges, subcategories and how "
        "many in-stock products suit each occasion. Use it when the shopper asks what the shop "
        "sells, or to pick a valid category and subcategory before get_products_by_category. "
        "Not needed before search_products. Call it at most once per conversation."
    ),
    response_model=CategoriesResponse,
)
def get_categories(request: Request) -> CategoriesResponse:
    categories = request.app.state.catalog.category_overview()
    request.state.result_count = len(categories)
    return CategoriesResponse(categories=categories)


def _resolve(catalog: Catalog, category: str, subcategory: str | None) -> tuple[str, str | None]:
    """Category slug and canonical subcategory, or a recoverable error with suggestions."""
    slug = catalog.resolve_category(category)
    if slug is None:
        raise category_not_found(
            category, catalog.suggest_categories(category), list(catalog.categories)
        )
    if subcategory is None:
        return slug, None
    sub = catalog.resolve_subcategory(slug, subcategory)
    if sub is None:
        raise subcategory_not_found(
            subcategory,
            slug,
            catalog.suggest_subcategories(slug, subcategory),
            catalog.subcategories[slug],
            catalog.categories_with_subcategory(subcategory),
        )
    return slug, sub


@router.get(
    "/categories/{category}/products",
    operation_id="get_products_by_category",
    summary="List the products in one category",
    description=(
        "List the products in one category, optionally narrowed by subcategory, price, recipient, "
        "occasion, delivery deadline or gift wrap. Use it when the shopper names a kind of "
        "product: 'a chef's knife' (subcategory Knives), 'something for the kitchen', 'your "
        "candles'. For gift requests defined by recipient, occasion or budget, use "
        "search_products instead. Use subcategory for a specific product type, so "
        "'outside_price_range' tells you about that type only. Products with 'also_listed_in' "
        "appear in two categories: never recommend both listings. If the category or subcategory "
        "does not exist, the response is {found: false, error} with 'did_you_mean': retry with "
        "it."
    ),
    response_model=ListResponse,
    response_model_exclude_unset=True,
)
def get_products_by_category(
    request: Request,
    category: str = Path(
        description="Category slug or display name, e.g. `kitchen-dining` or `Kitchen & Dining`.",
        examples=["kitchen-dining"],
    ),
    subcategory: str | None = Query(
        None,
        description="Subcategory within the category, e.g. `Knives`. Valid values are listed by "
        "get_categories.",
        examples=["Knives"],
    ),
    query: ListQuery = Depends(list_query),
) -> ListResponse:
    catalog: Catalog = request.app.state.catalog
    slug, sub = _resolve(catalog, category, subcategory)
    product_filter = replace(query.filter, category=slug, subcategory=sub)
    result = catalog.query(product_filter, query.sort, query.limit, query.offset)
    request.state.result_count = result.total
    ref = catalog.categories[slug]
    return list_response(result, query, product_filter, CategoryRef(slug=ref.slug, name=ref.name))
