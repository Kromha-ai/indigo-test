import hashlib
import json
import logging

import pytest

from tests.conftest import KEY


@pytest.fixture
def access_lines(caplog):
    caplog.set_level(logging.INFO, logger="catalog.access")

    def lines():
        return [json.loads(r.getMessage()) for r in caplog.records if r.name == "catalog.access"]

    return lines


def test_successful_call_is_logged_with_key_fingerprint(client, auth, access_lines):
    client.get("/categories", headers=auth)
    (line,) = access_lines()
    assert line["operation"] == "get_categories"
    assert line["status"] == 200
    assert line["result_count"] == 11
    assert line["error_code"] is None
    assert line["key_fingerprint"] == hashlib.sha256(KEY.encode()).hexdigest()[:6]
    assert line["latency_ms"] >= 0


def test_rejected_call_is_logged_without_fingerprint(client, access_lines):
    client.get("/categories", headers={"X-API-Key": "wrong"})
    (line,) = access_lines()
    assert line["status"] == 401
    assert line["error_code"] == "unauthorized"
    assert line["key_fingerprint"] is None


def test_key_never_appears_in_logs(client, auth, caplog, access_lines):
    caplog.set_level(logging.DEBUG)
    client.get("/categories?x=1", headers=auth)
    client.get("/categories", headers={"X-API-Key": "wrong-secret-value"})
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert KEY not in text
    assert "wrong-secret-value" not in text


def test_query_is_logged(client, auth, access_lines):
    client.get("/categories?debug=1", headers=auth)
    assert access_lines()[0]["query"] == "debug=1"
