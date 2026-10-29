# Catalogue build report

- **Built**: 2026-10-29 16:40 UTC
- **Source**: `gift-shop-catalog.csv`, SHA-256 `3e32e993f5d198a35ea8148cd8d02236718589a3700ebf34b35be99dd47aead6`
- **Records**: 152

## Category fixes

| Product | Raw value | Canonical |
|---|---|---|
| `HL-004` | `'home & living'` | Home & Living |
| `HL-013` | `'Home and Living'` | Home & Living |
| `HL-023` | `' Home & Living'` | Home & Living |
| `KD-009` | `'kitchen & dining'` | Kitchen & Dining |
| `TG-015` | `'Tech and Gadgets'` | Tech & Gadgets |
| `BS-006` | `'books & stationery'` | Books & Stationery |

## Cross-listed products

Same name, brand, price and description under different IDs. The first ID is primary.

- `HL-021` / `KD-024`
- `HL-024` / `KD-023`

## Constants

- `rating_mean` (C): 4.3735
- `rating_prior_weight` (m, 25th percentile of review counts): 96.0
- `low_stock_max`: 5

## Availability

- `in_stock`: 138
- `low_stock`: 3: `BW-016`, `HL-026`, `TG-025`
- `out_of_stock`: 11: `BS-007`, `BW-012`, `GP-007`, `HL-004`, `HL-022`, `JW-008`, `KD-007`, `KD-019`, `OT-008`, `PT-003`, `TG-022`

## Unrated products

`BS-014`, `EX-001`, `EX-002`, `HL-008`, `HL-026`

## Products per category

| Category | Products |
|---|---|
| Home & Living | 28 |
| Kitchen & Dining | 24 |
| Tech & Gadgets | 25 |
| Beauty & Wellness | 18 |
| Books & Stationery | 16 |
| Games & Puzzles | 12 |
| Outdoor & Travel | 10 |
| Jewellery | 8 |
| Kids | 6 |
| Pets | 3 |
| Experiences | 2 |
