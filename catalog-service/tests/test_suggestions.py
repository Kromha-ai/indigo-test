"""Empty results tell the agent which single constraint to relax."""


def get(client, auth, url):
    body = client.get(url, headers=auth).json()
    assert body["items"] == [] and body["total"] == 0
    return body["suggestions"]


def test_budget_too_low_suggests_raising_it(client, auth):
    suggestions = get(client, auth, "/products/search?occasion=housewarming&max_price=15")
    assert suggestions[0] == {"change": "raise max_price to 32", "would_match": 2}
    assert {"change": "remove the occasion filter", "would_match": 1} in suggestions


def test_suggestions_are_sorted_and_capped(client, auth):
    suggestions = get(client, auth, "/products/search?max_shipping_days=0&gift_wrap=true")
    counts = [s["would_match"] for s in suggestions]
    assert counts == sorted(counts, reverse=True) and len(suggestions) <= 3
    assert all(s["would_match"] > 0 for s in suggestions)


def test_out_of_stock_only_match_is_offered(client, auth):
    suggestions = get(client, auth, "/categories/pets/products?subcategory=Cats")
    changes = [s["change"] for s in suggestions]
    assert any("include_out_of_stock=true" in c for c in changes)
    assert "remove the subcategory filter" in changes


def test_raising_min_price_floor(client, auth):
    suggestions = get(client, auth, "/categories/kids/products?min_price=500")
    assert suggestions[0]["change"] == "lower min_price to 96"


def test_gift_wrap_relaxation(client, auth):
    suggestions = get(client, auth, "/categories/experiences/products?gift_wrap=true")
    assert suggestions == [{"change": "remove the gift_wrap filter", "would_match": 2}]


def test_browse_never_suggests_dropping_its_category(client, auth):
    suggestions = get(client, auth, "/categories/pets/products?occasion=graduation")
    assert all("category" not in s["change"] for s in suggestions)


def test_no_useful_relaxation_gives_no_suggestions(client, auth):
    assert get(client, auth, "/categories/home-living/products?recipient=kids&max_price=10") == []


def test_non_empty_results_have_no_suggestions(client, auth):
    body = client.get("/products/search?recipient=her", headers=auth).json()
    assert body["total"] > 0 and body["suggestions"] == []
