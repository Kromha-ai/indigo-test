"""Every error the agent can meet, with its recovery content."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def get(client, auth, url):
    return client.get(url, headers=auth)


@pytest.mark.parametrize(
    "raw,expected",
    [("electronics", "tech-gadgets"), ("toys", "kids"), ("jewelry", "jewellery"),
     ("Home and Kitchen", "home-living"), ("kitchn-dining", "kitchen-dining")],
)  # fmt: skip
def test_category_not_found_suggests(client, auth, raw, expected):
    response = get(client, auth, f"/categories/{raw}/products")
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False
    assert body["error"]["code"] == "category_not_found"
    assert body["error"]["did_you_mean"][0] == expected
    assert len(body["error"]["valid_values"]) == 11
    assert "get_categories" in body["error"]["hint"]


def test_subcategory_elsewhere(client, auth):
    body = get(client, auth, "/categories/home-living/products?subcategory=Books").json()
    assert body["found"] is False
    assert body["error"]["code"] == "subcategory_not_found"
    assert "books-stationery" in body["error"]["hint"] and "kids" in body["error"]["hint"]
    assert "Candles" in body["error"]["valid_values"]


def test_subcategory_typo(client, auth):
    body = get(client, auth, "/categories/home-living/products?subcategory=Candels").json()
    assert body["error"]["did_you_mean"] == ["Candles"]


def test_subcategory_singular_is_accepted(client, auth):
    body = get(client, auth, "/categories/home-living/products?subcategory=candle").json()
    assert body["found"] is True and body["applied_filters"]["subcategory"] == "Candles"


def test_product_not_found(client, auth):
    response = get(client, auth, "/products/XX-999")
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False
    assert body["error"]["code"] == "product_not_found"
    assert "did_you_mean" not in body["error"]


def test_product_typo_suggests_close_ids(client, auth):
    body = get(client, auth, "/products/HL-0O3").json()
    assert "HL-003" in body["error"]["did_you_mean"]


@pytest.mark.parametrize(
    "query,fragment",
    [("min_price=50&max_price=20", "max_price (20) must be greater than or equal to min_price"),
     ("limit=0", "limit"), ("limit=26", "limit"), ("recipient=grandma", "recipient"),
     ("occasion=wedding", "occasion"), ("max_shipping_days=99", "max_shipping_days"),
     ("min_price=-1", "min_price")],
)  # fmt: skip
def test_invalid_parameters(client, auth, query, fragment):
    response = get(client, auth, f"/categories/home-living/products?{query}")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_parameter"
    assert fragment in error["message"]
    assert "found" not in response.json()


def test_electronics_suggests_only_tech_gadgets(client, auth):
    body = get(client, auth, "/categories/electronics/products").json()
    assert body["error"]["did_you_mean"] == ["tech-gadgets"]


@pytest.mark.parametrize(
    "method,path,status",
    [("get", "/nope", 404), ("get", "/products/", 404), ("get", "/categories//products", 404),
     ("post", "/categories", 405)],
)  # fmt: skip
def test_unknown_routes_use_the_envelope(client, auth, method, path, status):
    response = client.request(method, path, headers=auth)
    assert response.status_code == status
    assert response.json()["error"]["code"] == "route_not_found"
    assert "found" not in response.json()


@pytest.mark.parametrize(
    "path",
    ["/categories/electronics/products", "/categories/home-living/products?subcategory=Books",
     "/products/XX-999", "/categories/home-living/products?limit=0", "/nope"],
)  # fmt: skip
def test_every_error_carries_a_hint(client, auth, path):
    error = get(client, auth, path).json()["error"]
    assert error["code"] and error["message"] and error["hint"]


def test_unexpected_failure_uses_the_envelope(settings, catalog):
    app = create_app(settings, catalog)

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error" and error["hint"]
    assert "secret detail" not in response.text
