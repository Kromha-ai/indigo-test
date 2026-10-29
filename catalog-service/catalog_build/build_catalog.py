"""Build the normalised catalogue from the client's raw CSV export.

The raw export is never modified. This module reads it, applies every normalisation
and derivation rule, and writes:

- data/catalog.json            loaded by the service
- data/catalog.normalized.csv  the same records, flat, for people
- data/BUILD_REPORT.md         every fix applied, the constants, the source checksum

Run from catalog-service/:  uv run python -m catalog_build.build_catalog
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import statistics
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = SERVICE_ROOT.parent / "raw_data" / "gift-shop-catalog.csv"
DEFAULT_SYNONYMS = Path(__file__).resolve().parent / "synonyms.toml"
DEFAULT_OUT = SERVICE_ROOT / "data"

SCHEMA_VERSION = 1

CATEGORIES = [
    "Home & Living",
    "Kitchen & Dining",
    "Tech & Gadgets",
    "Beauty & Wellness",
    "Books & Stationery",
    "Games & Puzzles",
    "Outdoor & Travel",
    "Jewellery",
    "Kids",
    "Pets",
    "Experiences",
]
RECIPIENTS = ["her", "him", "couple", "kids", "anyone"]
OCCASIONS = ["birthday", "thank-you", "christmas", "housewarming", "anniversary", "graduation"]
ANYONE_MATCHES = ["anyone", "her", "him", "couple"]  # never "kids"

EXPECTED_COLUMNS = [
    "product_id", "name", "category", "subcategory", "brand", "price_eur", "stock", "rating",
    "reviews_count", "recipient", "occasion", "tags", "color", "material", "gift_wrap",
    "shipping_days", "description",
]  # fmt: skip

LOW_STOCK_MAX = 5


class BuildError(Exception):
    """The export cannot be normalised. Nothing is written."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


@dataclass
class BuildResult:
    catalog: dict
    source_sha256: str
    category_fixes: list[tuple[str, str, str]] = field(default_factory=list)  # id, raw, canonical
    cross_listings: list[list[str]] = field(default_factory=list)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("&", " ")).strip("-")


def category_key(raw: str) -> str:
    key = " ".join(raw.strip().lower().split())
    return key.replace(" and ", " & ")


CATEGORY_BY_KEY = {category_key(name): name for name in CATEGORIES}


def split_list(raw: str) -> list[str]:
    return [part.strip().lower() for part in raw.split("|") if part.strip()]


def optional(raw: str) -> str | None:
    value = raw.strip()
    return value or None


@dataclass
class ParsedRow:
    record: dict | None  # None when the row has problems
    problems: list[str]
    category_fix: tuple[str, str, str] | None = None  # id, raw value, canonical name


def _non_negative_int(raw: str) -> int | None:
    try:
        value = int(raw.strip())
    except ValueError:
        return None
    return value if value >= 0 else None


def _price(raw: str) -> Decimal | None:
    try:
        price = Decimal(raw.strip()).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return price if price >= 0 else None


def _parse_row(row: dict) -> ParsedRow:
    pid = row["product_id"].strip()
    problems: list[str] = []

    def report_problem(message: str) -> None:
        problems.append(f"{pid}: {message}")

    category_fix = None
    canonical = CATEGORY_BY_KEY.get(category_key(row["category"]))
    if canonical is None:
        report_problem(f"unknown category {row['category']!r}")
    elif row["category"] != canonical:
        category_fix = (pid, row["category"], canonical)

    price = _price(row["price_eur"])
    if price is None:
        report_problem(f"unparseable price {row['price_eur']!r}")

    stock = _non_negative_int(row["stock"])
    if stock is None:
        report_problem(f"unparseable stock {row['stock']!r}")
    shipping_days = _non_negative_int(row["shipping_days"])
    if shipping_days is None:
        report_problem(f"unparseable shipping_days {row['shipping_days']!r}")

    rating = reviews = None
    if row["rating"].strip():
        try:
            rating = float(row["rating"])
        except ValueError:
            report_problem(f"unparseable rating {row['rating']!r}")
    if row["reviews_count"].strip():
        reviews = _non_negative_int(row["reviews_count"])
        if reviews is None:
            report_problem(f"unparseable reviews_count {row['reviews_count']!r}")

    recipient = row["recipient"].strip().lower()
    if recipient not in RECIPIENTS:
        report_problem(f"unknown recipient {row['recipient']!r}")

    occasions = split_list(row["occasion"])
    for occasion in occasions:
        if occasion not in OCCASIONS:
            report_problem(f"unknown occasion {occasion!r}")

    gift_wrap = row["gift_wrap"].strip().lower()
    if gift_wrap not in ("yes", "no"):
        report_problem(f"unparseable gift_wrap {row['gift_wrap']!r}")

    if problems:
        return ParsedRow(record=None, problems=problems)

    subcategory = row["subcategory"].strip()
    record = {
        "product_id": pid,
        "name": row["name"].strip(),
        "category": canonical,
        "category_slug": slugify(canonical),
        "subcategory": subcategory,
        "subcategory_slug": slugify(subcategory),
        "brand": row["brand"].strip(),
        "price_eur": float(price),
        "stock": stock,
        "availability": (
            "out_of_stock" if stock == 0 else "low_stock" if stock <= LOW_STOCK_MAX else "in_stock"
        ),
        "rating": rating,
        "reviews_count": reviews,
        "is_rated": rating is not None,
        "recipient": recipient,
        "recipients_match": ANYONE_MATCHES if recipient == "anyone" else [recipient],
        "occasions": occasions,
        "tags": split_list(row["tags"]),
        "color": optional(row["color"]),
        "material": optional(row["material"]),
        "gift_wrap": gift_wrap == "yes",
        "shipping_days": shipping_days,
        "is_digital": shipping_days == 0,
        "description": row["description"].strip(),
    }
    return ParsedRow(record=record, problems=[], category_fix=category_fix)


def _rating_constants(products: list[dict]) -> tuple[float, float]:
    rated = [p for p in products if p["is_rated"] and p["reviews_count"] is not None]
    mean_rating = statistics.mean(p["rating"] for p in rated)
    prior_weight = statistics.quantiles([p["reviews_count"] for p in rated], n=4)[0]
    return mean_rating, prior_weight


def _link_cross_listings(products: list[dict], result: BuildResult) -> None:
    groups: dict[tuple, list[dict]] = {}
    for product in products:
        key = (product["name"], product["brand"], product["price_eur"], product["description"])
        groups.setdefault(key, []).append(product)
    for listings in groups.values():
        ids = sorted(p["product_id"] for p in listings)
        primary = ids[0]
        for product in listings:
            product["listing_group"] = primary
            product["is_primary_listing"] = product["product_id"] == primary
            product["also_listed_in"] = [
                {"product_id": other["product_id"], "category_slug": other["category_slug"]}
                for other in sorted(listings, key=lambda p: p["product_id"])
                if other is not product
            ]
        if len(listings) > 1:
            result.cross_listings.append(ids)


def build(source: Path = DEFAULT_SOURCE, synonyms: Path = DEFAULT_SYNONYMS) -> BuildResult:
    raw = source.read_bytes()
    result = BuildResult(catalog={}, source_sha256=hashlib.sha256(raw).hexdigest())
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    if reader.fieldnames != EXPECTED_COLUMNS:
        raise BuildError([f"unexpected columns {reader.fieldnames!r}"])

    problems: list[str] = []
    products = []
    seen_ids: set[str] = set()
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            problems.append(f"{row.get('product_id', '?')}: wrong number of fields")
            continue
        if row["product_id"].strip() in seen_ids:
            problems.append(f"{row['product_id']}: duplicate product_id")
            continue
        seen_ids.add(row["product_id"].strip())
        parsed = _parse_row(row)
        problems.extend(parsed.problems)
        if parsed.record is not None:
            products.append(parsed.record)
        if parsed.category_fix is not None:
            result.category_fixes.append(parsed.category_fix)
    if problems:
        raise BuildError(problems)

    products.sort(key=lambda p: p["product_id"])
    mean_rating, prior_weight = _rating_constants(products)
    for product in products:
        if product["is_rated"]:
            v, r = product["reviews_count"], product["rating"]
            score = (v / (v + prior_weight)) * r + (prior_weight / (v + prior_weight)) * mean_rating
        else:
            score = mean_rating
        product["rating_score"] = round(score, 4)
    _link_cross_listings(products, result)

    synonym_table = tomllib.loads(synonyms.read_text(encoding="utf-8"))["category_synonyms"]
    slugs = {slugify(name) for name in CATEGORIES}
    unknown = sorted(set(synonym_table.values()) - slugs)
    if unknown:
        raise BuildError([f"synonyms.toml points to unknown category slugs {unknown}"])

    result.catalog = {
        "schema_version": SCHEMA_VERSION,
        "constants": {
            "rating_mean": round(mean_rating, 4),
            "rating_prior_weight": prior_weight,
            "low_stock_max": LOW_STOCK_MAX,
        },
        "categories": [{"slug": slugify(name), "name": name} for name in CATEGORIES],
        "recipients": RECIPIENTS,
        "occasions": OCCASIONS,
        "category_synonyms": dict(sorted(synonym_table.items())),
        "products": products,
    }
    return result


def catalog_json(result: BuildResult) -> str:
    return json.dumps(result.catalog, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


CSV_COLUMNS = [
    "product_id", "name", "category", "category_slug", "subcategory", "subcategory_slug", "brand",
    "price_eur", "stock", "availability", "rating", "reviews_count", "rating_score", "recipient",
    "occasions", "tags", "color", "material", "gift_wrap", "shipping_days", "is_digital",
    "listing_group", "description",
]  # fmt: skip


def normalized_csv(result: BuildResult) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for product in result.catalog["products"]:
        row = []
        for column in CSV_COLUMNS:
            value = product[column]
            if isinstance(value, list):
                value = "|".join(value)
            elif isinstance(value, bool):
                value = "yes" if value else "no"
            elif value is None:
                value = ""
            elif column == "price_eur":
                value = f"{value:.2f}"
            row.append(value)
        writer.writerow(row)
    return out.getvalue()


def build_report(result: BuildResult, source: Path, built_at: datetime) -> str:
    products = result.catalog["products"]
    constants = result.catalog["constants"]
    lines = [
        "# Catalogue build report",
        "",
        f"- **Built**: {built_at:%Y-%m-%d %H:%M} UTC",
        f"- **Source**: `{source.name}`, SHA-256 `{result.source_sha256}`",
        f"- **Records**: {len(products)}",
        "",
        "## Category fixes",
        "",
        "| Product | Raw value | Canonical |",
        "|---|---|---|",
        *(f"| `{pid}` | `{raw!r}` | {canon} |" for pid, raw, canon in result.category_fixes),
        "",
        "## Cross-listed products",
        "",
        "Same name, brand, price and description under different IDs. The first ID is primary.",
        "",
        *(f"- {' / '.join(f'`{i}`' for i in ids)}" for ids in result.cross_listings),
        "",
        "## Constants",
        "",
        f"- `rating_mean` (C): {constants['rating_mean']}",
        f"- `rating_prior_weight` (m, 25th percentile of review counts): "
        f"{constants['rating_prior_weight']}",
        f"- `low_stock_max`: {constants['low_stock_max']}",
        "",
        "## Availability",
        "",
    ]
    for state in ("in_stock", "low_stock", "out_of_stock"):
        ids = [p["product_id"] for p in products if p["availability"] == state]
        detail = "" if state == "in_stock" else ": " + ", ".join(f"`{i}`" for i in ids)
        lines.append(f"- `{state}`: {len(ids)}{detail}")
    unrated = [p["product_id"] for p in products if not p["is_rated"]]
    lines += [
        "",
        "## Unrated products",
        "",
        ", ".join(f"`{i}`" for i in unrated) or "None.",
        "",
        "## Products per category",
        "",
        "| Category | Products |",
        "|---|---|",
    ]
    for category in result.catalog["categories"]:
        count = sum(p["category_slug"] == category["slug"] for p in products)
        lines.append(f"| {category['name']} | {count} |")
    return "\n".join(lines) + "\n"


def write_outputs(result: BuildResult, out_dir: Path, source: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "catalog.json").write_text(catalog_json(result), encoding="utf-8")
    (out_dir / "catalog.normalized.csv").write_text(normalized_csv(result), encoding="utf-8")
    report = build_report(result, source, datetime.now(UTC))
    (out_dir / "BUILD_REPORT.md").write_text(report, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--synonyms", type=Path, default=DEFAULT_SYNONYMS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    try:
        result = build(args.source, args.synonyms)
    except BuildError as error:
        print("Build failed, nothing written:", file=sys.stderr)
        for problem in error.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    write_outputs(result, args.out, args.source)
    products = result.catalog["products"]
    print(
        f"Built {len(products)} records: {len(result.category_fixes)} category fixes, "
        f"{len(result.cross_listings)} cross-listed pairs → {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
