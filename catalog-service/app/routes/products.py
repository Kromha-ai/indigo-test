from fastapi import APIRouter, Path, Request

from app.catalog import Catalog
from app.errors import product_not_found
from app.models import ProductDetail, ProductDetailResponse

router = APIRouter(tags=["catalogue"])


@router.get(
    "/products/{product_id}",
    operation_id="get_product_details",
    summary="Get one product's full record",
    description=(
        "Get the full record for one product: description, materials, colour, gift wrap, "
        "shipping time and availability. Call it for each of the 2–3 products before "
        "recommending them (in parallel), and whenever the shopper asks about a specific item. "
        "The description is what makes a good reason. Out-of-stock products are returned too, "
        "with availability 'out_of_stock'. An unknown ID returns {found: false, error} with "
        "'did_you_mean'."
    ),
    response_model=ProductDetailResponse,
    response_model_exclude_unset=True,
)
def get_product_details(
    request: Request,
    product_id: str = Path(
        description="Product ID from a list response, e.g. `HL-003` (case-insensitive).",
        examples=["HL-003"],
    ),
) -> ProductDetailResponse:
    catalog: Catalog = request.app.state.catalog
    record = catalog.resolve_product(product_id)
    if record is None:
        raise product_not_found(product_id, catalog.suggest_products(product_id))
    request.state.result_count = 1
    return ProductDetailResponse(found=True, product=ProductDetail.from_record(record))
