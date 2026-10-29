from fastapi import APIRouter, Request

from app.models import CategoriesResponse

router = APIRouter(tags=["catalogue"])


@router.get(
    "/categories",
    operation_id="get_categories",
    summary="List the shop's categories",
    description=(
        "List the shop's categories with product counts, price ranges, subcategories and how "
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
