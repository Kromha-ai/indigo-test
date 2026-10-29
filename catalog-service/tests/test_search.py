"""search_products, against the real catalogue (spec acceptance criteria)."""

import pytest


@pytest.fixture
def search(client, auth):
    def call(**params):
        return client.get("/products/search", params=params, headers=auth)

    return call


def ids(body):
    return [item["product_id"] for item in body["items"]]


def test_housewarming_40_60_returns_13_without_duplicate(search):
    body = search(occasion="housewarming", min_price=40, max_price=60).json()
    assert body["total"] == 13
    assert "HL-024" in ids(body) and "KD-023" not in ids(body)
    assert len(set(ids(body))) == len(ids(body))
    assert "found" not in body and "category" not in body


def test_cross_listed_products_appear_once(search):
    body = search(max_price=1000, limit=25).json()
    seen = ids(body) + ids(search(max_price=1000, limit=25, offset=25).json())
    for page in range(2, 6):
        seen += ids(search(max_price=1000, limit=25, offset=25 * page).json())
    assert "HL-021" in seen and "KD-024" not in seen
    assert "HL-024" in seen and "KD-023" not in seen
    assert len(seen) == len(set(seen)) == 141 - 2  # in stock, minus the two duplicate listings


def test_kids_returns_only_kids_products(search):
    body = search(recipient="kids").json()
    assert ids(body) and all(pid.startswith("KI-") for pid in ids(body))


def test_search_spans_categories(search):
    body = search(occasion="housewarming", min_price=40, max_price=60).json()
    assert {i["category"] for i in body["items"]} >= {
        "home-living",
        "kitchen-dining",
        "experiences",
    }


def test_search_has_no_category_parameter(client):
    spec = client.get("/openapi.json").json()
    names = [p["name"] for p in spec["paths"]["/products/search"]["get"]["parameters"]]
    assert "category" not in names and "subcategory" not in names


def test_no_filters_returns_the_best_rated_products(search):
    response = search()
    assert response.status_code == 200
    body = response.json()
    assert body["applied_filters"] == {}
    assert (body["total"], body["returned"], body["next_offset"]) == (139, 10, 10)
    assert ids(body)[0] == "TG-006"  # top rating_score in the shop
    assert all(i["availability"] != "out_of_stock" for i in body["items"])


@pytest.mark.parametrize(
    "params", [{"include_out_of_stock": "true"}, {"sort": "price_asc"}, {"gift_wrap": "false"}]
)
def test_stock_sort_and_gift_wrap_false_do_not_narrow(search, params):
    body = search(**params).json()
    assert body["total"] == (150 if params.get("include_out_of_stock") else 139)


def test_search_reports_outside_price_range(search):
    body = search(occasion="housewarming", min_price=40, max_price=60).json()
    assert body["outside_price_range"]["above_max"]["min_price_eur"] == 62.0
    assert body["outside_price_range"]["below_min"]["max_price_eur"] == 36.0


def test_search_is_not_captured_as_a_product_id(client, auth):
    response = client.get("/products/search?recipient=her", headers=auth)
    assert "items" in response.json()


def test_internal_filter_is_not_echoed(search):
    assert "primary_only" not in search(recipient="her").json()["applied_filters"]


def test_default_page_and_budget(search):
    response = search(max_price=1000, limit=25)
    assert response.json()["returned"] == 25
    assert len(response.text) / 3.6 < 2600
    assert search(max_price=1000).json()["returned"] == 10
