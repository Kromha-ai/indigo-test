def test_eleven_categories_counting_every_product(client, auth):
    categories = client.get("/categories", headers=auth).json()["categories"]
    assert len(categories) == 11
    assert sum(c["product_count"] for c in categories) == 152


def test_overview_carries_no_product_level_detail(client, auth):
    # Occasions and prices per product belong to search and browse, not to the category map.
    categories = client.get("/categories", headers=auth).json()["categories"]
    expected = {
        "slug",
        "name",
        "product_count",
        "in_stock_count",
        "price_range_eur",
        "subcategories",
    }
    assert all(set(c) == expected for c in categories)


def test_home_living_overview(client, auth):
    categories = client.get("/categories", headers=auth).json()["categories"]
    home = next(c for c in categories if c["slug"] == "home-living")
    assert home == {
        "slug": "home-living",
        "name": "Home & Living",
        "product_count": 28,
        "in_stock_count": 26,
        "price_range_eur": {"min": 28.0, "max": 249.0},
        "subcategories": [
            "Candles",
            "Decor",
            "Fragrance",
            "Garden",
            "Lighting",
            "Storage",
            "Textiles",
            "Vases",
        ],  # fmt: skip
    }


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["products_loaded"] == 152
