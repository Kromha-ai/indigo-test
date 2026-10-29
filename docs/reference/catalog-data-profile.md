# Catalogue Data Profile

**Last updated**: 2026-10-29
**Source**: `raw_data/gift-shop-catalog.csv` (client export, received as-is; never edited in place)

This document records what the raw export actually contains. Every normalisation rule in `docs/specs/CATALOG_SPEC.md` traces back to a finding here. The fixes are applied by the build step, which writes the normalised catalogue and a per-row report to `catalog-service/data/`; the raw file stays as received. If the client sends a new export, re-run the profile and update this file first.

---

## Shape

- 152 rows, 17 columns, UTF-8, comma-separated, RFC 4180 quoting (names and descriptions contain commas).
- No ragged rows, no extra columns.
- `product_id` is unique, and every ID matches `^[A-Z]{2}-\d{3}$`. The two-letter prefix encodes the category (`HL` Home & Living, `KD` Kitchen & Dining, `TG` Tech & Gadgets, `BW` Beauty & Wellness, `BS` Books & Stationery, `GP` Games & Puzzles, `OT` Outdoor & Travel, `JW` Jewellery, `KI` Kids, `PT` Pets, `EX` Experiences).

## Columns

| Column | Type in CSV | Empty | Notes |
|---|---|---|---|
| `product_id` | string | 0 | Unique, stable key |
| `name` | string | 0 | 150 distinct: two names appear twice (see *Cross-listed products*) |
| `category` | string | 0 | 17 raw spellings of **11** real categories (see below) |
| `subcategory` | string | 0 | 48 values, consistently cased. `Books`, `Craft` and `Fragrance` appear under more than one category |
| `brand` | string | 0 | 22 brands. `indigo Gift Shop` is the house brand (gift cards only) |
| `price_eur` | decimal | 0 | €6.50 – €899.00, median €68. `TG-025` (€899 speakers) is a legitimate outlier |
| `stock` | int | 0 | 11 products at `0`. `999` on gift cards is a sentinel for unlimited stock |
| `rating` | decimal | 5 | 3.6 – 4.9. Empty means *no reviews yet*, not zero |
| `reviews_count` | int | 5 | Empty exactly when `rating` is empty |
| `recipient` | enum | 0 | `anyone` (90), `him` (29), `her` (20), `couple` (7), `kids` (6) |
| `occasion` | pipe list | 3 | `birthday`, `thank-you`, `christmas`, `housewarming`, `anniversary`, `graduation` |
| `tags` | pipe list | 0 | 380 distinct tags, mostly used only once. Useful for free-text matching, useless as a filter vocabulary |
| `color` | string | 2 | Empty on gift cards |
| `material` | string | 2 | Empty on gift cards |
| `gift_wrap` | `yes`/`no` | 0 | 139 yes, 13 no |
| `shipping_days` | int | 0 | 0 – 7. `0` only on the digital gift cards (instant delivery by email) |
| `description` | string | 0 | At most 142 characters. Short, opinionated selling copy |

## Defects and quirks

### Category spelling drift

Six rows use a non-canonical spelling of their category:

| Row | Raw value | Canonical |
|---|---|---|
| `HL-004` | `home & living` | Home & Living |
| `HL-013` | `Home and Living` | Home & Living |
| `HL-023` | ` Home & Living` (leading space) | Home & Living |
| `KD-009` | `kitchen & dining` | Kitchen & Dining |
| `TG-015` | `Tech and Gadgets` | Tech & Gadgets |
| `BS-006` | `books & stationery` | Books & Stationery |

Grouping on the raw value would show 17 categories and silently hide these products from their real category. The ID prefix agrees with the canonical category in every case.

### Cross-listed products

Two products appear twice, under different IDs and categories, with identical brand, price, stock, rating, reviews, occasions and description:

| Primary | Duplicate | Product |
|---|---|---|
| `HL-021` (Home & Living / Garden) | `KD-024` (Kitchen & Dining / Serving) | Herb Garden Kit |
| `HL-024` (Home & Living / Decor) | `KD-023` (Kitchen & Dining / Serving) | Amber Glass Tumbler Set |

The identical stock figures suggest a single physical SKU listed twice, not two items. Without handling, a cross-category search for *"housewarming, around €50"* returns the Amber Glass Tumbler Set twice. The spec treats them as one product with two listings.

### Out of stock

`HL-004`, `HL-022`, `KD-007`, `KD-019`, `TG-022`, `BW-012`, `BS-007`, `GP-007`, `OT-008`, `JW-008`, `PT-003` have `stock = 0`.

Low stock (1–5 units): `HL-026` (4), `BW-016` (3), `TG-025` (2).

### Missing values

- No rating or reviews: `HL-008`, `HL-026`, `BS-014`, `EX-001`, `EX-002`.
- No occasion: `HL-013`, `TG-020`, `BS-015`.
- No colour or material: `EX-001`, `EX-002`.

### Recipient semantics

`anyone` is a wildcard for adults, but not for children. The `anyone` bucket contains chef's knives (`KD-001`, `KD-002`), fragrance and bar accessories. Only the six `KI-*` products are tagged `kids`.

## Reference queries

These are useful as fixtures and as sanity checks for the agent:

- **In stock, €40–€60, occasion `housewarming`**: 14 rows, 13 distinct products (the tumbler set appears twice), including the €50 gift card.
- **Recipient `couple`**: 7 products (`KD-017`, `KD-018`, `BW-015`, `GP-003`, `GP-012`, `OT-007`, `OT-010`).
- **Shipping ≥ 5 days**: 14 products. These matter for "I need it by Friday" requests.
