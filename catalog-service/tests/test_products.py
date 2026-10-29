def test_detail_by_id_is_case_insensitive(client, auth):
    body = client.get("/products/hl-003", headers=auth).json()
    assert body["found"] is True
    product = body["product"]
    assert product["product_id"] == "HL-003"
    assert product["description"].startswith("Cedar, black pepper")
    assert product["also_listed_in"] == []
    assert "stock" not in product and "rating_score" not in product


def test_out_of_stock_product_is_still_returned(client, auth):
    product = client.get("/products/TG-022", headers=auth).json()["product"]
    assert product["availability"] == "out_of_stock"


def test_cross_listed_detail(client, auth):
    product = client.get("/products/KD-023", headers=auth).json()["product"]
    assert product["also_listed_in"] == [{"product_id": "HL-024", "category_slug": "home-living"}]


def test_gift_card_detail(client, auth):
    product = client.get("/products/EX-001", headers=auth).json()["product"]
    assert product["is_digital"] is True and product["shipping_days"] == 0
    assert product["color"] is None and product["rating"] is None
