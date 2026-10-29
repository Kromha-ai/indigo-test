"""get_products_by_category, against the real catalogue (spec acceptance criteria)."""

import json

import pytest


@pytest.fixture
def browse(client, auth):
    def call(category, **params):
        return client.get(f"/categories/{category}/products", params=params, headers=auth).json()

    return call


def ids(body):
    return [item["product_id"] for item in body["items"]]


@pytest.mark.parametrize(
    "name", ["home-living", "Home and Living", " home & LIVING ", "Home & Living"]
)
def test_category_resolves_by_slug_or_name(browse, name):
    body = browse(name)
    assert body["found"] is True
    assert body["category"] == {"slug": "home-living", "name": "Home & Living"}
    assert body["applied_filters"]["category"] == "home-living"


def test_default_page_and_pagination(browse):
    first = browse("home-living")
    assert (first["total"], first["returned"], first["offset"], first["next_offset"]) == (
        26, 10, 0, 10,
    )  # fmt: skip
    second = browse("home-living", offset=10)
    assert (second["returned"], second["next_offset"]) == (10, 20)
    third = browse("home-living", offset=20)
    assert (third["returned"], third["next_offset"]) == (6, None)
    all_ids = ids(first) + ids(second) + ids(third)
    assert len(set(all_ids)) == 26
    assert "HL-013" in all_ids  # drifted 'Home and Living' row lands in its category


def test_offset_past_the_end(browse):
    body = browse("home-living", offset=100)
    assert body["items"] == [] and body["total"] == 26 and body["next_offset"] is None


def test_limit_bounds(browse):
    assert browse("home-living", limit=1)["returned"] == 1
    assert browse("home-living", limit=25)["returned"] == 25


def test_out_of_stock_excluded_unless_asked(browse):
    assert "HL-004" not in ids(browse("home-living", limit=25)) + ids(
        browse("home-living", limit=25, offset=25)
    )
    included = browse("home-living", include_out_of_stock=True, subcategory="Candles")
    assert "HL-004" in ids(included)
    assert included["applied_filters"]["include_out_of_stock"] is True


def test_cross_listed_product_is_flagged(browse):
    body = browse("home-living", occasion="housewarming", min_price=40, max_price=60)
    tumblers = next(i for i in body["items"] if i["product_id"] == "HL-024")
    assert tumblers["also_listed_in"] == [
        {"product_id": "KD-023", "category_slug": "kitchen-dining"}
    ]
    others = [i for i in body["items"] if i["product_id"] != "HL-024"]
    assert all("also_listed_in" not in i for i in others)


def test_knives_under_budget_report_the_chef_knife(browse):
    body = browse("kitchen-dining", subcategory="knives", max_price=100)
    assert sorted(ids(body)) == ["KD-002", "KD-003"]
    assert body["applied_filters"] == {
        "category": "kitchen-dining", "subcategory": "Knives", "max_price": 100.0,
    }  # fmt: skip
    assert body["outside_price_range"] == {"above_max": {"count": 1, "min_price_eur": 149.0}}


def test_below_min_is_reported(browse):
    body = browse("kitchen-dining", subcategory="Knives", min_price=60)
    assert body["outside_price_range"] == {"below_min": {"count": 1, "max_price_eur": 54.0}}


def test_no_price_filter_no_outside_range(browse):
    assert "outside_price_range" not in browse("kitchen-dining")


def test_best_rated_puts_the_e_reader_first(browse):
    assert ids(browse("tech-gadgets"))[0] == "TG-006"


def test_price_sorts(browse):
    asc = [i["price_eur"] for i in browse("pets", sort="price_asc")["items"]]
    desc = [i["price_eur"] for i in browse("pets", sort="price_desc")["items"]]
    assert asc == sorted(asc) and desc == sorted(desc, reverse=True)


def test_kids_category_and_kids_recipient(browse):
    assert all(pid.startswith("KI-") for pid in ids(browse("kids")))
    assert browse("home-living", recipient="kids")["total"] == 0


def test_her_includes_anyone(browse):
    recipients = {i["recipient"] for i in browse("home-living", recipient="her", limit=25)["items"]}
    assert recipients == {"her", "anyone"}


def test_gift_wrap_false_is_not_a_filter(browse):
    body = browse("experiences", gift_wrap=False)
    assert body["total"] == 2 and "gift_wrap" not in body["applied_filters"]
    assert browse("experiences", gift_wrap=True)["applied_filters"]["gift_wrap"] is True


def test_shipping_and_gift_wrap_filters(browse):
    fast = browse("experiences", max_shipping_days=0)
    assert sorted(ids(fast)) == ["EX-001", "EX-002"]
    wrapped = browse("experiences", gift_wrap=True)
    assert wrapped["total"] == 0  # gift cards cannot be wrapped


def test_summary_shape(browse):
    item = browse("home-living", limit=1)["items"][0]
    assert set(item) == {
        "product_id", "name", "category", "subcategory", "brand", "price_eur", "rating",
        "reviews_count", "availability", "recipient", "occasions", "tags", "shipping_days",
    }  # fmt: skip


def test_unrated_products_show_null_rating(browse):
    vases = browse("home-living", subcategory="Vases")
    hl008 = next(i for i in vases["items"] if i["product_id"] == "HL-008")
    assert hl008["rating"] is None and hl008["reviews_count"] is None


def test_response_budget(client, auth):
    response = client.get("/categories/home-living/products?limit=25", headers=auth)
    assert response.json()["returned"] == 25
    assert len(response.text) / 3.6 < 2600


def test_result_count_is_logged(client, auth, caplog):
    import logging

    caplog.set_level(logging.INFO, logger="catalog.access")
    client.get("/categories/kitchen-dining/products?subcategory=Knives", headers=auth)
    line = json.loads(caplog.records[-1].getMessage())
    assert (line["operation"], line["result_count"]) == ("get_products_by_category", 3)
