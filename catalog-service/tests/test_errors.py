"""Every error the agent can meet, with its recovery content."""

import pytest


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


def test_unknown_route_is_not_an_internal_error(client, auth):
    assert get(client, auth, "/nope").status_code == 404
