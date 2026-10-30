import pytest

from app.settings import SERVICE_ROOT, ConfigError, Settings
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


TOOL_PATHS = [
    "/categories",
    "/categories/home-living/products",
    "/products/search",
    "/products/HL-001",
]


@pytest.mark.parametrize("path", TOOL_PATHS)
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "nope"}, {"X-API-Key": ""}])
def test_every_tool_rejects_a_missing_or_wrong_key(client, path, headers):
    response = client.get(path, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


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


def test_unset_variables_keep_the_defaults():
    settings = Settings.from_env({"CATALOG_API_KEYS": "a"})
    assert settings == Settings(api_keys=("a",))
    assert settings.rate_limit_per_minute == 600


def test_overrides_are_read_from_env():
    settings = Settings.from_env(
        {
            "CATALOG_API_KEYS": "a",
            "CATALOG_DATA_PATH": "data/other.json",
            "PUBLIC_BASE_URL": "https://catalog.example.test/",
            "RATE_LIMIT_PER_MINUTE": "5",
            "LOG_LEVEL": "DEBUG",
        }
    )
    assert settings.data_path == SERVICE_ROOT / "data" / "other.json"
    assert settings.public_base_url == "https://catalog.example.test"
    assert settings.rate_limit_per_minute == 5
    assert settings.log_level == "DEBUG"


def test_absolute_data_path_is_kept(tmp_path):
    env = {"CATALOG_API_KEYS": "a", "CATALOG_DATA_PATH": str(tmp_path / "c.json")}
    assert Settings.from_env(env).data_path == tmp_path / "c.json"


@pytest.mark.parametrize("value", ["abc", "0"])
def test_bad_rate_limit_refuses_to_start(value):
    with pytest.raises(ConfigError, match="RATE_LIMIT_PER_MINUTE"):
        Settings.from_env({"CATALOG_API_KEYS": "a", "RATE_LIMIT_PER_MINUTE": value})
