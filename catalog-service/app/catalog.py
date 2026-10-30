"""In-memory catalogue: the queries the routes need, with no HTTP concerns."""

from __future__ import annotations

import difflib
import re
from collections.abc import Callable
from dataclasses import dataclass, field, fields, replace
from datetime import UTC, datetime

from app.domain import Availability, Occasion, Recipient, SortOrder
from app.loader import CatalogFile, ProductRecord


def _key(text: str) -> str:
    """Lowercase, single spaces, `and` → `&`: `' Home and  Living'` → `home & living`."""
    return " ".join(text.strip().lower().split()).replace(" and ", " & ")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("&", " ")).strip("-")


def _singular(text: str) -> str:
    return text[:-1] if text.endswith("s") and not text.endswith("ss") else text


def one_edit_apart(a: str, b: str) -> bool:
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b, strict=True)) == 1
    short, long = sorted((a, b), key=len)
    return any(long[:i] + long[i + 1 :] == short for i in range(len(long)))


@dataclass(frozen=True)
class ProductFilter:
    category: str | None = None  # slug
    subcategory: str | None = None  # canonical name
    min_price: float | None = None
    max_price: float | None = None
    recipient: Recipient | None = None
    occasion: Occasion | None = None
    max_shipping_days: int | None = None
    gift_wrap: bool = False
    include_out_of_stock: bool = False
    # Search shows each cross-listed product once, through its primary listing. Internal:
    # not a caller-facing filter, so never echoed in `applied`.
    primary_only: bool = field(default=False, metadata={"internal": True})

    def checks(self) -> list[Callable[[ProductRecord], bool]]:
        """One predicate per filter that is set, price excluded (see `in_price_band`)."""
        checks: list[Callable[[ProductRecord], bool]] = []
        if self.category is not None:
            checks.append(lambda p: p.category_slug == self.category)
        if self.subcategory is not None:
            checks.append(lambda p: p.subcategory == self.subcategory)
        if not self.include_out_of_stock:
            checks.append(lambda p: p.availability != Availability.out_of_stock)
        if self.recipient is not None:
            checks.append(lambda p: self.recipient in p.recipients_match)
        if self.occasion is not None:
            checks.append(lambda p: self.occasion in p.occasions)
        if (max_days := self.max_shipping_days) is not None:
            checks.append(lambda p: p.shipping_days <= max_days)
        if self.gift_wrap:
            checks.append(lambda p: p.gift_wrap)
        if self.primary_only:
            checks.append(lambda p: p.is_primary_listing)
        return checks

    @property
    def has_price_band(self) -> bool:
        return self.min_price is not None or self.max_price is not None

    def in_price_band(self, p: ProductRecord) -> bool:
        return (self.min_price is None or p.price_eur >= self.min_price) and (
            self.max_price is None or p.price_eur <= self.max_price
        )

    def applied(self) -> dict[str, object]:
        """The filters that are set, as echoed back to the caller."""
        applied: dict[str, object] = {}
        for f in fields(self):
            if f.metadata.get("internal"):
                continue
            value = getattr(self, f.name)
            if value is not None and value != f.default:
                applied[f.name] = value
        return applied


@dataclass
class QueryResult:
    items: list[ProductRecord]
    total: int
    # Prices of products passing every other filter but outside the band; None when the
    # corresponding bound is not set.
    prices_above_max: list[float] | None = None
    prices_below_min: list[float] | None = None
    # When nothing matches: (change in plain words, products it would match), best first.
    suggestions: list[tuple[str, int]] = field(default_factory=list)


# Filters an empty result may suggest dropping, with the wording used for the agent.
RELAXABLE = {
    "occasion": "remove the occasion filter",
    "recipient": "remove the recipient filter",
    "subcategory": "remove the subcategory filter",
    "max_shipping_days": "remove the delivery deadline (max_shipping_days)",
    "gift_wrap": "remove the gift_wrap filter",
}
MAX_SUGGESTIONS = 3


SORT_KEYS = {
    SortOrder.best_rated: lambda p: (-p.rating_score, p.product_id),
    SortOrder.price_asc: lambda p: (p.price_eur, -p.rating_score, p.product_id),
    SortOrder.price_desc: lambda p: (-p.price_eur, -p.rating_score, p.product_id),
}


class Catalog:
    def __init__(self, data: CatalogFile):
        self.data = data
        self.loaded_at = datetime.now(UTC)
        self.products: list[ProductRecord] = data.products
        self.by_id = {p.product_id: p for p in self.products}
        self.categories = {c.slug: c for c in data.categories}
        self.subcategories: dict[str, list[str]] = {
            slug: sorted({p.subcategory for p in self.products if p.category_slug == slug})
            for slug in self.categories
        }

    # --- categories ---------------------------------------------------------------------------

    def category_overview(self) -> list[dict]:
        overview = []
        for category in self.data.categories:
            products = [p for p in self.products if p.category_slug == category.slug]
            in_stock = [p for p in products if p.availability != Availability.out_of_stock]
            prices = [p.price_eur for p in products]
            overview.append(
                {
                    "slug": category.slug,
                    "name": category.name,
                    "product_count": len(products),
                    "in_stock_count": len(in_stock),
                    "price_range_eur": {"min": min(prices), "max": max(prices)},
                    "subcategories": self.subcategories[category.slug],
                }
            )
        return overview

    def resolve_category(self, raw: str) -> str | None:
        """Slug for a slug or display name, ignoring case, spacing and `and`/`&`."""
        key, slug = _key(raw), _slugify(raw)
        for category in self.data.categories:
            if slug == category.slug or key == _key(category.name):
                return category.slug
        return None

    def suggest_categories(self, raw: str) -> list[str]:
        key = _key(raw)
        synonyms = self.data.category_synonyms
        found: list[str] = []
        for candidate in [key, _slugify(raw), *re.split(r"[^a-z0-9]+", key)]:
            if candidate in synonyms:
                found.append(synonyms[candidate])
        names = {_key(c.name): c.slug for c in self.data.categories}
        names.update({c.slug: c.slug for c in self.data.categories})
        for match in difflib.get_close_matches(key, list(names), n=3, cutoff=0.6):
            found.append(names[match])
        return list(dict.fromkeys(found))[:3]

    def resolve_subcategory(self, category: str, raw: str) -> str | None:
        wanted = _singular(_key(raw))
        for name in self.subcategories[category]:
            if _singular(_key(name)) == wanted:
                return name
        return None

    def suggest_subcategories(self, category: str, raw: str) -> list[str]:
        options = {_key(n): n for n in self.subcategories[category]}
        return [options[m] for m in difflib.get_close_matches(_key(raw), list(options), n=3)]

    def categories_with_subcategory(self, raw: str) -> list[str]:
        wanted = _singular(_key(raw))
        return [
            slug
            for slug, names in self.subcategories.items()
            if any(_singular(_key(n)) == wanted for n in names)
        ]

    # --- products -----------------------------------------------------------------------------

    def resolve_product(self, raw: str) -> ProductRecord | None:
        return self.by_id.get(raw.strip().upper())

    def suggest_products(self, raw: str) -> list[str]:
        wanted = raw.strip().upper()
        return sorted(pid for pid in self.by_id if one_edit_apart(wanted, pid))[:3]

    def _select(self, f: ProductFilter) -> list[ProductRecord]:
        """Products passing every non-price filter."""
        checks = f.checks()
        return [p for p in self.products if all(check(p) for check in checks)]

    def count(self, f: ProductFilter) -> int:
        return sum(1 for p in self._select(f) if f.in_price_band(p))

    def query(self, f: ProductFilter, sort: SortOrder, limit: int, offset: int) -> QueryResult:
        candidates = self._select(f)
        matching = sorted(filter(f.in_price_band, candidates), key=SORT_KEYS[sort])
        result = QueryResult(items=matching[offset : offset + limit], total=len(matching))
        if f.max_price is not None:
            result.prices_above_max = [p.price_eur for p in candidates if p.price_eur > f.max_price]
        if f.min_price is not None:
            result.prices_below_min = [p.price_eur for p in candidates if p.price_eur < f.min_price]
        if not matching:
            result.suggestions = self._relaxations(f, candidates)
        return result

    def _relaxations(
        self, f: ProductFilter, candidates: list[ProductRecord]
    ) -> list[tuple[str, int]]:
        """One relaxation at a time, kept only if it would return something."""
        defaults = {field_.name: field_.default for field_ in fields(f)}
        options: list[tuple[str, int]] = []
        for name, wording in RELAXABLE.items():
            if getattr(f, name) != defaults[name]:
                options.append((wording, self.count(replace(f, **{name: defaults[name]}))))
        if f.max_price is not None:
            above = [p.price_eur for p in candidates if p.price_eur > f.max_price]
            if above:
                nearest = min(above)
                options.append(
                    (f"raise max_price to {nearest:g}", self.count(replace(f, max_price=nearest)))
                )
        if f.min_price is not None:
            below = [p.price_eur for p in candidates if p.price_eur < f.min_price]
            if below:
                nearest = max(below)
                options.append(
                    (f"lower min_price to {nearest:g}", self.count(replace(f, min_price=nearest)))
                )
        if not f.include_out_of_stock:
            in_or_out = self.count(replace(f, include_out_of_stock=True))
            options.append(
                ("set include_out_of_stock=true (those cannot be bought now)", in_or_out)
            )
        useful = [option for option in options if option[1] > 0]
        useful.sort(key=lambda option: -option[1])
        return useful[:MAX_SUGGESTIONS]
