from fastapi import APIRouter, Request

from app.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, include_in_schema=False)
def health(request: Request) -> HealthResponse:
    catalog = request.app.state.catalog
    return HealthResponse(
        status="ok",
        products_loaded=len(catalog.products),
        catalog_loaded_at=catalog.loaded_at,
    )
