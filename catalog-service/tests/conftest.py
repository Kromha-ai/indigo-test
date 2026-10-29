import pytest
from fastapi.testclient import TestClient

from app.catalog import Catalog
from app.loader import load_catalog
from app.main import create_app
from app.settings import SERVICE_ROOT, Settings

KEY = "test-key"
OTHER_KEY = "second-key"
PUBLIC_URL = "https://catalog.example.test"


@pytest.fixture(scope="session")
def catalog() -> Catalog:
    return Catalog(load_catalog(SERVICE_ROOT / "data" / "catalog.json"))


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(api_keys=(KEY, OTHER_KEY), public_base_url=PUBLIC_URL)


@pytest.fixture(scope="session")
def client(settings, catalog) -> TestClient:
    return TestClient(create_app(settings, catalog))


@pytest.fixture
def auth() -> dict[str, str]:
    return {"X-API-Key": KEY}
