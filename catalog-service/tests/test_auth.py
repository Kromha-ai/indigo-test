import pytest

from app.settings import ConfigError, Settings
from tests.conftest import KEY, OTHER_KEY


def test_missing_key_is_rejected(client):
    response = client.get("/categories")
    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Missing or invalid API key.",
            "hint": "Send a valid key in the X-API-Key header.",
        }
    }


def test_wrong_key_is_rejected(client):
    assert client.get("/categories", headers={"X-API-Key": "nope"}).status_code == 401


@pytest.mark.parametrize("key", [KEY, OTHER_KEY])
def test_every_configured_key_is_accepted(client, key):
    assert client.get("/categories", headers={"X-API-Key": key}).status_code == 200


def test_key_is_not_accepted_as_query_parameter(client):
    assert client.get(f"/categories?api_key={KEY}").status_code == 401


@pytest.mark.parametrize("path", ["/health", "/openapi.json", "/docs", "/redoc"])
def test_open_routes_need_no_key(client, path):
    assert client.get(path).status_code == 200


def test_refuses_to_start_without_keys():
    with pytest.raises(ConfigError):
        Settings.from_env({"CATALOG_API_KEYS": " , "})


def test_keys_are_parsed_from_env():
    settings = Settings.from_env({"CATALOG_API_KEYS": "a, b ,,c"})
    assert settings.api_keys == ("a", "b", "c")
