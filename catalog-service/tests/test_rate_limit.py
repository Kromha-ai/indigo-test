import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.ratelimit import RateLimiter
from app.settings import ConfigError, Settings
from tests.conftest import KEY, OTHER_KEY


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def limited(catalog):
    clock = FakeClock()
    app = create_app(Settings(api_keys=(KEY, OTHER_KEY), rate_limit_per_minute=3), catalog)
    app.state.rate_limiter = RateLimiter(3, clock=clock)
    return TestClient(app), clock


def get(client, key=KEY):
    return client.get("/categories", headers={"X-API-Key": key})


def test_over_the_limit_gets_429_with_retry_after(limited):
    client, clock = limited
    for _ in range(3):
        assert get(client).status_code == 200
    clock.now += 20
    response = get(client)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "40"
    assert response.json() == {
        "error": {
            "code": "rate_limited",
            "message": "Too many requests for this API key.",
            "hint": "Retry after the number of seconds in Retry-After.",
        }
    }


def test_window_slides(limited):
    client, clock = limited
    for _ in range(3):
        get(client)
    clock.now += 60
    assert get(client).status_code == 200


def test_each_key_has_its_own_limit(limited):
    client, _ = limited
    for _ in range(3):
        get(client)
    assert get(client).status_code == 429
    assert get(client, OTHER_KEY).status_code == 200


def test_rejected_requests_do_not_count(limited):
    client, _ = limited
    for _ in range(3):
        get(client)
    for _ in range(5):
        assert get(client).status_code == 429
    assert get(client, OTHER_KEY).status_code == 200


def test_invalid_keys_are_not_rate_limited_but_rejected(limited):
    client, _ = limited
    for _ in range(5):
        assert get(client, "nope").status_code == 401


def test_open_routes_are_not_rate_limited(limited):
    client, _ = limited
    for _ in range(5):
        assert client.get("/health").status_code == 200


def test_limit_must_be_positive():
    with pytest.raises(ConfigError):
        Settings(api_keys=("k",), rate_limit_per_minute=0)
