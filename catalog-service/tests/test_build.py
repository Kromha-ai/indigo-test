"""The build step against the real export (acceptance criteria) and small fixture CSVs."""

from pathlib import Path

import pytest

from app.settings import SERVICE_ROOT
from catalog_build.build_catalog import (
    EXPECTED_COLUMNS,
    BuildError,
    build,
    catalog_json,
    normalized_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def real():
    return build()


@pytest.fixture(scope="module")
def products(real):
    return {p["product_id"]: p for p in real.catalog["products"]}


def write_csv(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "export.csv"
    path.write_text(",".join(EXPECTED_COLUMNS) + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


GOOD = "HL-001,Lamp,Home & Living,Lighting,B,10.00,3,4.5,10,anyone,birthday,lamp,,,yes,2,Nice."


# --- real export ---------------------------------------------------------------------------


def test_every_row_becomes_a_record(real):
    assert len(real.catalog["products"]) == 152


def test_eleven_categories(real, products):
    assert len(real.catalog["categories"]) == 11
    assert {p["category_slug"] for p in products.values()} == {
        c["slug"] for c in real.catalog["categories"]
    }


@pytest.mark.parametrize(
    "pid,category",
    [
        ("HL-004", "Home & Living"),
        ("HL-013", "Home & Living"),
        ("HL-023", "Home & Living"),
        ("KD-009", "Kitchen & Dining"),
        ("TG-015", "Tech & Gadgets"),
        ("BS-006", "Books & Stationery"),
    ],
)
def test_drifted_category_spellings_are_fixed(products, pid, category):
    assert products[pid]["category"] == category


def test_report_lists_the_six_category_fixes(real):
    assert sorted(fix[0] for fix in real.category_fixes) == [
        "BS-006", "HL-004", "HL-013", "HL-023", "KD-009", "TG-015",
    ]  # fmt: skip


def test_cross_listed_pairs_are_linked(real, products):
    assert sorted(real.cross_listings) == [["HL-021", "KD-024"], ["HL-024", "KD-023"]]
    assert products["KD-023"]["listing_group"] == "HL-024"
    assert products["HL-024"]["is_primary_listing"] is True
    assert products["KD-023"]["is_primary_listing"] is False
    assert products["HL-024"]["also_listed_in"] == [
        {"product_id": "KD-023", "category_slug": "kitchen-dining"}
    ]
    assert products["HL-001"]["also_listed_in"] == []


def test_unrated_products_stay_null(products):
    unrated = sorted(pid for pid, p in products.items() if p["rating"] is None)
    assert unrated == ["BS-014", "EX-001", "EX-002", "HL-008", "HL-026"]
    assert all(products[pid]["reviews_count"] is None for pid in unrated)


def test_kids_never_matches_anyone_products(products):
    for p in products.values():
        if p["recipient"] == "anyone":
            assert "kids" not in p["recipients_match"]
    assert products["KD-001"]["recipients_match"] == ["anyone", "her", "him", "couple"]


def test_rating_constants_and_ranking(real, products):
    constants = real.catalog["constants"]
    assert constants["rating_mean"] == pytest.approx(4.37, abs=0.01)
    assert constants["rating_prior_weight"] == 96
    best = max(products.values(), key=lambda p: p["rating_score"])
    assert best["product_id"] == "TG-006"
    assert products["EX-001"]["rating_score"] == constants["rating_mean"]


def test_availability_bands(products):
    assert products["HL-004"]["availability"] == "out_of_stock"
    assert products["TG-025"]["availability"] == "low_stock"
    assert products["HL-001"]["availability"] == "in_stock"
    assert sum(p["availability"] == "out_of_stock" for p in products.values()) == 11


def test_gift_cards_are_digital(products):
    assert products["EX-001"]["is_digital"] is True
    assert products["EX-001"]["color"] is None


def test_build_is_deterministic():
    first, second = build(), build()
    assert catalog_json(first) == catalog_json(second)
    assert normalized_csv(first) == normalized_csv(second)


def test_committed_catalog_is_not_stale(real):
    committed = (SERVICE_ROOT / "data" / "catalog.json").read_text(encoding="utf-8")
    assert committed == catalog_json(real), (
        "data/catalog.json is stale: run `uv run python -m catalog_build.build_catalog`"
    )


# --- fixture CSVs ----------------------------------------------------------------------------


def test_minimal_fixture_builds():
    result = build(FIXTURES / "minimal.csv")
    by_id = {p["product_id"]: p for p in result.catalog["products"]}
    assert by_id["HL-003"]["category"] == "Home & Living"
    assert by_id["KD-001"]["recipients_match"] == ["kids"]
    assert by_id["KD-001"]["occasions"] == []


@pytest.mark.parametrize(
    "row,problem",
    [
        (GOOD.replace("Home & Living", "Garden Stuff"), "unknown category"),
        (GOOD.replace("10.00", "ten"), "unparseable price"),
        (GOOD.replace(",anyone,", ",grandma,"), "unknown recipient"),
        (GOOD.replace(",birthday,", ",wedding,"), "unknown occasion"),
        (GOOD.replace(",3,4.5", ",-1,4.5"), "unparseable stock"),
        (GOOD.replace(",yes,2,", ",maybe,2,"), "unparseable gift_wrap"),
        (GOOD.replace("10.00", "NaN"), "unparseable price"),
        (GOOD.replace("HL-001", "HL-1"), "does not match AA-000"),
        (GOOD.replace("HL-001", "KD-001"), "ID prefix does not match"),
        (GOOD.replace(",Lamp,", ",,"), "empty name"),
        (GOOD.replace(",Nice.", ", "), "empty description"),
        (GOOD.replace(",4.5,10,", ",0,10,"), "outside"),
        (GOOD.replace(",4.5,10,", ",nan,10,"), "outside"),
        (GOOD.replace(",4.5,10,", ",4.5,0,"), "not a positive integer"),
        (GOOD.replace(",4.5,10,", ",,10,"), "both set or both empty"),
        (GOOD.replace(",4.5,10,", ",4.5,,"), "both set or both empty"),
    ],
)
def test_bad_rows_abort_the_build(tmp_path, row, problem):
    with pytest.raises(BuildError) as error:
        build(write_csv(tmp_path, GOOD.replace("HL-001", "HL-002"), row))
    assert any(problem in p for p in error.value.problems)


def test_duplicate_ids_abort_the_build(tmp_path):
    with pytest.raises(BuildError, match="duplicate product_id"):
        build(write_csv(tmp_path, GOOD, GOOD))


def test_unexpected_columns_abort_the_build(tmp_path):
    path = tmp_path / "export.csv"
    path.write_text("product_id,name\nXX-001,Lamp\n", encoding="utf-8")
    with pytest.raises(BuildError, match="unexpected columns"):
        build(path)
