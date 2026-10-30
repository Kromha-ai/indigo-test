"""The OpenAPI document is the product: the platform imports it and the LLM reads it."""

import pytest

from tests.conftest import PUBLIC_URL

FRAMEWORK_SCHEMAS = {"HTTPValidationError", "ValidationError"}


@pytest.fixture(scope="module")
def spec(client):
    return client.get("/openapi.json").json()


def operations(spec):
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            yield path, method, operation


def test_openapi_3_1(spec):
    assert spec["openapi"].startswith("3.1")


def test_servers_is_the_public_url(spec):
    assert spec["servers"] == [{"url": PUBLIC_URL}]


def test_every_operation_is_described(spec):
    for path, method, operation in operations(spec):
        assert operation.get("operationId"), f"{method} {path} has no operationId"
        assert operation.get("summary"), f"{method} {path} has no summary"
        assert len(operation.get("description", "")) > 80, f"{method} {path}: thin description"


def test_every_parameter_is_described(spec):
    for path, method, operation in operations(spec):
        for parameter in operation.get("parameters", []):
            assert parameter.get("description"), f"{method} {path}: {parameter['name']}"


def test_no_header_parameters(spec):
    for path, method, operation in operations(spec):
        for parameter in operation.get("parameters", []):
            assert parameter["in"] != "header", f"{method} {path} declares a header parameter"


def test_every_response_field_is_described(spec):
    for name, schema in spec["components"]["schemas"].items():
        if name in FRAMEWORK_SCHEMAS:
            continue
        for field, definition in schema.get("properties", {}).items():
            assert definition.get("description"), f"{name}.{field} has no description"


def test_api_key_is_a_security_scheme(spec):
    assert spec["components"]["securitySchemes"]["ApiKeyAuth"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key issued by the service operator, sent in the X-API-Key header.",
    }
    for path, method, operation in operations(spec):
        assert operation.get("security") == [{"ApiKeyAuth": []}], f"{method} {path}"


def test_tools_present(spec):
    assert {op["operationId"] for _, _, op in operations(spec)} == {
        "get_categories",
        "get_products_by_category",
        "search_products",
        "get_product_details",
    }


def test_health_is_not_a_tool(spec):
    assert "/health" not in spec["paths"]


@pytest.mark.parametrize(
    "schema", ["ListResponse", "ProductSummary", "ProductDetail", "CategoriesResponse"]
)
def test_response_schemas_expose_their_fields(spec, schema):
    # A custom serializer can silently turn a model into an opaque object in the document,
    # hiding every field description from the LLM.
    properties = spec["components"]["schemas"][schema].get("properties", {})
    assert properties, f"{schema} is published without its fields"


def test_vocabularies_are_enums(spec):
    schemas = spec["components"]["schemas"]
    assert schemas["Availability"]["enum"] == ["in_stock", "low_stock", "out_of_stock"]
    assert "anyone" in schemas["Recipient"]["enum"]
    assert "thank-you" in schemas["Occasion"]["enum"]
