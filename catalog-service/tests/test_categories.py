def test_eleven_categories_counting_every_product(client, auth):
    categories = client.get("/categories", headers=auth).json()["categories"]
    assert len(categories) == 11
    assert sum(c["product_count"] for c in categories) == 152


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
        "in_stock_by_occasion": {
            "housewarming": 18,
            "thank-you": 9,
            "christmas": 6,
            "anniversary": 5,
            "birthday": 4,
            "graduation": 1,
        },  # fmt: skip
    }


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["products_loaded"] == 152
