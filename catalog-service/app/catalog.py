"""In-memory catalogue: the queries the routes need, with no HTTP concerns."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from app.loader import CatalogFile, ProductRecord


class Catalog:
    def __init__(self, data: CatalogFile):
        self.data = data
        self.loaded_at = datetime.now(UTC)
        self.products: list[ProductRecord] = data.products
        self.by_id = {p.product_id: p for p in self.products}

    def category_overview(self) -> list[dict]:
        overview = []
        for category in self.data.categories:
            products = [p for p in self.products if p.category_slug == category.slug]
            in_stock = [p for p in products if p.availability != "out_of_stock"]
            occasions = Counter(o for p in in_stock for o in p.occasions)
            prices = [p.price_eur for p in products]
            overview.append(
                {
                    "slug": category.slug,
                    "name": category.name,
                    "product_count": len(products),
                    "in_stock_count": len(in_stock),
                    "price_range_eur": {"min": min(prices), "max": max(prices)},
                    "subcategories": sorted({p.subcategory for p in products}),
                    "in_stock_by_occasion": dict(occasions.most_common()),
                }
            )
        return overview
