import json

import pytest

from app.loader import CatalogLoadError, load_catalog
from app.settings import SERVICE_ROOT

REAL = SERVICE_ROOT / "data" / "catalog.json"


def test_real_catalog_loads():
    assert len(load_catalog(REAL).products) == 152


def test_missing_file(tmp_path):
    with pytest.raises(CatalogLoadError, match="not found"):
        load_catalog(tmp_path / "nope.json")


def test_truncated_file(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(REAL.read_text()[:500])
    with pytest.raises(CatalogLoadError, match="not valid JSON"):
        load_catalog(path)


def test_hand_edited_record(tmp_path):
    data = json.loads(REAL.read_text())
    data["products"][0]["availability"] = "plenty"
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data))
    with pytest.raises(CatalogLoadError, match="record model"):
        load_catalog(path)


def test_unknown_field(tmp_path):
    data = json.loads(REAL.read_text())
    data["products"][0]["surprise"] = True
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data))
    with pytest.raises(CatalogLoadError):
        load_catalog(path)
