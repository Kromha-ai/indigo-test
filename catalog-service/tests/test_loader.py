import json

import pytest

from app.loader import CatalogLoadError, load_catalog
from app.main import create_app
from app.settings import SERVICE_ROOT, Settings

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


def edited(tmp_path, edit):
    data = json.loads(REAL.read_text())
    edit(data, {p["product_id"]: p for p in data["products"]})
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data))
    return path


def set_fields(pid, **fields):
    return lambda data, by_id: by_id[pid].update(fields)


def drop_category(slug):
    def edit(data, by_id):
        data["products"] = [p for p in data["products"] if p["category_slug"] != slug]

    return edit


@pytest.mark.parametrize(
    "edit,problem",
    [
        (set_fields("HL-001", product_id="HL-1"), "does not match"),
        (set_fields("HL-001", price_eur=float("nan")), "invalid price_eur"),
        (set_fields("HL-008", rating=0.0), "disagree"),
        (set_fields("HL-001", rating=7.0), "outside 1–5"),
        (set_fields("HL-001", stock=0), "availability disagrees"),
        (set_fields("HL-001", stock=2), "availability disagrees"),
        (set_fields("EX-001", is_digital=False), "is_digital"),
        (set_fields("KD-001", recipients_match=["anyone", "kids"]), "recipients_match"),
        (lambda data, by_id: data["products"].append(by_id["HL-001"]), "duplicate product_id"),
        (drop_category("pets"), "pets has no products"),
        (set_fields("HL-001", category_slug="kitchen-dining"), "mixes ID prefixes"),
        (lambda data, by_id: data["category_synonyms"].update(telly="television"),
         "unknown categories"),
        (set_fields("HL-024", also_listed_in=[]), "does not list it back"),
        (set_fields("HL-001", also_listed_in=[{"product_id": "XX-999",
                                               "category_slug": "kids"}]), "is wrong"),
        (set_fields("KD-023", is_primary_listing=True), "only primary"),
    ],
)  # fmt: skip
def test_inconsistent_catalogue_fails(tmp_path, edit, problem):
    with pytest.raises(CatalogLoadError, match=problem):
        load_catalog(edited(tmp_path, edit))


def test_startup_fails_on_an_invalid_catalogue(tmp_path):
    path = edited(tmp_path, set_fields("HL-001", stock=0))
    with pytest.raises(CatalogLoadError):
        create_app(Settings(api_keys=("k",), data_path=path))
