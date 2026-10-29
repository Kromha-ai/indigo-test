---
Status: Approved
Last updated: 2026-10-29
---

# Spec: Catalog Service

The contract of the service: what it is and what it does. The reasoning behind it is in `archive/catalog-spec-decisions.md` (decisions D2–D7) and `AUTHENTICATION.md` (D1).

## Purpose

Turn the client's CSV catalogue export into a small, authenticated, read-only HTTP API. Its OpenAPI document becomes the tool collection of the gift assistant on the indigo.ai platform (`docs/specs/AGENT_SPEC.md`). The consumer is an LLM, so responses are sized for its context window, and descriptions and errors are written for it to act on.

Context: `docs/reference/scenario.md`. Data facts: `docs/reference/catalog-data-profile.md`.

## Out of scope

- Writes of any kind (orders, carts, stock reservations).
- A database: the catalogue is loaded into memory at startup.
- Free-text, keyword or semantic search (D5, D7).
- Product images and storefront URLs (not in the export).
- Multi-language catalogue content (the agent handles the shopper's language).
- Admin UI and hot reload: a new export means rebuild, review, redeploy.

## Stack

Python 3.12 · FastAPI + Pydantic v2 · Uvicorn · `uv` · `pytest` + `TestClient` · `ruff` · one `Dockerfile`. Code lives in `catalog-service/` (see its `CLAUDE.md`).

## Data

### Build pipeline

The raw export is never modified. A build step turns it into the normalised catalogue the service loads.

```
raw_data/gift-shop-catalog.csv                 (client export, read-only)
   │  catalog_build/build_catalog.py  +  catalog_build/synonyms.toml (category synonyms)
   ▼
catalog-service/data/catalog.json              (loaded by the service)
catalog-service/data/catalog.normalized.csv    (same records, flat, for people)
catalog-service/data/BUILD_REPORT.md           (every fix per row, constants, source SHA-256)
```

- **Command**: `uv run python -m catalog_build.build_catalog` (from `catalog-service/`).
- **Deterministic and committed**: same input, byte-identical output. A test fails if the committed `catalog.json` is stale.
- **Fails loudly**: the build aborts on an unparseable price, stock or shipping value, an unknown category, recipient or occasion. The service refuses to start if `catalog.json` fails validation.
- The Docker image ships `data/catalog.json` only, not the raw CSV.

### Normalisation

| Raw | Rule |
|---|---|
| `category` | Trim, lowercase, ` and ` → ` & `, map to one of 11 canonical names (17 raw spellings) |
| `subcategory`, `brand`, `name`, `color`, `material` | Trim; empty → `null` |
| `description` | Trim |
| `price_eur` | Decimal, 2 places |
| `stock` | Int; internal only |
| `rating`, `reviews_count` | Empty → `null`, never 0 |
| `recipient` | Enum: `her`, `him`, `couple`, `kids`, `anyone` |
| `occasion`, `tags` | Split on `|`, trim, lowercase; empty → `[]` |
| `gift_wrap` | `yes`/`no` → bool |
| `shipping_days` | Int; `0` = digital, instant |

### Record

| Field | Notes |
|---|---|
| `product_id`, `name`, `brand`, `description`, `price_eur`, `color`, `material`, `gift_wrap`, `shipping_days`, `recipient`, `occasions`, `tags`, `rating`, `reviews_count` | As normalised |
| `category`, `category_slug`, `subcategory`, `subcategory_slug` | Slugs are the API identifiers (`home-living`) |
| `availability` | `in_stock`, `low_stock` (1–5), `out_of_stock`. Replaces the raw count |
| `is_rated`, `is_digital` | Derived booleans |
| `also_listed_in` | Other listings of the same product: `[{product_id, category_slug}]` |
| *Internal*: `stock`, `rating_score`, `recipients_match`, `listing_group`, `is_primary_listing` | Never serialised |

Derived rules:

- **`rating_score`** (ranking only): `(v/(v+m))·R + (m/(v+m))·C`, where `R` = rating, `v` = review count, `C` = mean rating (currently 4.37), `m` = 25th percentile of review counts (currently 96). `C` and `m` are computed at build time and recorded in the report. Unrated products get `C`.
- **`recipients_match`**: `anyone` matches `anyone`, `her`, `him` and `couple`, **never** `kids`. Every other value matches only itself.
- **Cross-listings**: an exact match on name, brand, price and description groups `HL-021`/`KD-024` and `HL-024`/`KD-023`. The lowest ID is primary. Browsing shows each listing in its own category; search returns the primary only; both IDs resolve in details.

## API

All responses are JSON. Each tool's `operationId` is its tool name.

| Tool | Route | Auth |
|---|---|---|
| `get_categories` | `GET /categories` | API key |
| `get_products_by_category` | `GET /categories/{category}/products` | API key |
| `search_products` | `GET /products/search` (declared before `/products/{product_id}`) | API key |
| `get_product_details` | `GET /products/{product_id}` | API key |
| — | `GET /health`, `GET /openapi.json`, `GET /docs`, `GET /redoc` | none |

### `get_categories`

No parameters. All 11 categories, each with `slug`, `name`, `product_count`, `in_stock_count`, `price_range_eur`, `subcategories` and `in_stock_by_occasion`:

```json
{"slug": "home-living", "name": "Home & Living", "product_count": 28, "in_stock_count": 26,
 "price_range_eur": {"min": 28.00, "max": 249.00},
 "subcategories": ["Candles", "Decor", "Fragrance", "Garden", "Lighting", "Storage", "Textiles", "Vases"],
 "in_stock_by_occasion": {"housewarming": 18, "thank-you": 9, "christmas": 6, "anniversary": 5, "birthday": 4, "graduation": 1}}
```

### `get_products_by_category` and `search_products`

Both return a `ListResponse` of `ProductSummary` items and share these parameters:

| Param | Type | Default | Constraint |
|---|---|---|---|
| `min_price`, `max_price` | number | — | ≥ 0; `max_price` ≥ `min_price` |
| `recipient` | enum | — | See *Filters* |
| `occasion` | enum | — | `birthday`, `thank-you`, `christmas`, `housewarming`, `anniversary`, `graduation` |
| `max_shipping_days` | int | — | 0–14 |
| `gift_wrap` | bool | — | `true` = wrappable only |
| `include_out_of_stock` | bool | `false` | |
| `sort` | enum | `best_rated` | `best_rated` (by `rating_score`), `price_asc`, `price_desc` |
| `limit` | int | `15` | 1–25 |
| `offset` | int | `0` | ≥ 0 |

They differ as follows:

- **`get_products_by_category`**: `category` (path, slug or display name, case-insensitive) is required; `subcategory` (case-insensitive; singular or plural, so `candle` finds `Candles`) is optional. For a shopper who names a kind of product.
- **`search_products`**: an optional `category` narrows the search. With no filters it returns the shop's best-rated in-stock products, within the usual page size. It returns one listing per product. For gift requests defined by constraints.

### `get_product_details`

`product_id` (path, case-insensitive). Returns `{"found": true, "product": ProductDetail}`. It also returns out-of-stock products, with `availability: out_of_stock`.

### Shapes

**`ProductSummary`** (about 95 tokens):

```json
{"product_id": "HL-003", "name": "Ember Ceramic Candle", "category": "home-living", "subcategory": "Candles",
 "brand": "Fold Studio", "price_eur": 42.00, "rating": 4.8, "reviews_count": 431, "availability": "in_stock",
 "recipient": "anyone", "occasions": ["thank-you", "birthday", "christmas"],
 "tags": ["candle", "scented", "woody", "refillable"], "shipping_days": 2}
```

`also_listed_in` is added only for cross-listed products.

**`ProductDetail`**: the summary plus `description`, `color`, `material`, `gift_wrap`, `is_digital` and `also_listed_in` (always present).

**`ListResponse`**:

```json
{"found": true, "category": {"slug": "kitchen-dining", "name": "Kitchen & Dining"},
 "items": [], "total": 2, "returned": 2, "offset": 0, "next_offset": null,
 "applied_filters": {"subcategory": "Knives", "max_price": 100},
 "outside_price_range": {"above_max": {"count": 1, "min_price_eur": 149.00}},
 "suggestions": []}
```

- `found: true` and `category` are on browse responses only. An unknown `category` on either list tool returns the recoverable `category_not_found` (`found: false`).
- `applied_filters` echoes the normalised input.
- `outside_price_range` (present when a price filter is set) counts the products that match every other filter but fall outside the band: `above_max: {count, min_price_eur}` and/or `below_min: {count, max_price_eur}`, each carrying the nearest price.
- `suggestions`: see *Empty results*.

### Response budget

| Tool | Default | Maximum |
|---|---|---|
| `get_categories` | about 1k tokens | grows with categories, not products |
| List tools | 15 summaries, about 1.5k tokens | 25 summaries, about 2.5k tokens |
| `get_product_details` | about 175 tokens | grows with the description (not cut) |

Descriptions never appear in lists. `total` and `next_offset` signal more results. The response shape does not depend on catalogue size.

### Filters

- **Recipient**: matches through `recipients_match`.
- **Occasion**: the value is in `occasions`. Products with no occasions never match.
- **Price**: inclusive.
- **Stock**: out-of-stock products are excluded unless `include_out_of_stock=true`.
- `recipient`, `occasion` and `sort` are OpenAPI enums.

### Empty results

`200` with `items: []` and up to 3 `suggestions`, each a single relaxation that would return matches, sorted by `would_match`:

```json
{"items": [], "total": 0, "suggestions": [{"change": "raise max_price to 25", "would_match": 4}]}
```

Relaxations tried: drop `occasion`, `recipient`, `subcategory`, `max_shipping_days` or `gift_wrap`; widen the price band to the nearest match; include out of stock.

### Errors

All errors use one envelope. **Recoverable** cases return `200` with `found: false` (D2); failures keep their HTTP status.

```json
{"found": false, "error": {"code": "category_not_found", "message": "No category matches 'electronics'.",
 "hint": "Use one of the slugs in 'did_you_mean', or call get_categories.",
 "did_you_mean": ["tech-gadgets"], "valid_values": ["home-living", "..."]}}
```

| Code | HTTP | Recovery content |
|---|---|---|
| `category_not_found` | 200, `found: false` | `did_you_mean` (fuzzy match plus `synonyms.toml`: *electronics* → `tech-gadgets`, *toys* → `kids`...), `valid_values` |
| `subcategory_not_found` | 200, `found: false` | That category's subcategories; `did_you_mean` if another category has it |
| `product_not_found` | 200, `found: false` | `hint` to search or browse; `did_you_mean` for IDs one edit away |
| `unauthorized` | 401 | `hint` names the header |
| `invalid_parameter` | 422 | Plain-language message per field |
| `rate_limited` | 429 | `Retry-After` |
| `internal_error` | 500 | Generic message, no stack trace |

### Authentication

Details in `AUTHENTICATION.md`.

- Static API key in `X-API-Key`, HTTPS only. Keys come from `CATALOG_API_KEYS` (comma-separated, one per consumer and environment) and are compared in constant time.
- The service refuses to start without keys.
- Rate limit: 120 requests per minute per key, returning `429`.
- Only `/health` and the documentation routes are open.

### OpenAPI document

- **Published publicly** at `https://catalog.builtbykromha.com/openapi.json`, plus `/docs` and `/redoc` (FastAPI defaults, never disabled). The indigo.ai tool collection imports it from that URL.
- **Auth** is a dependency on the data routers, not middleware, so the documentation routes stay open. Declared as an `apiKey` scheme. **Never** a header parameter.
- `servers[0].url` = `PUBLIC_BASE_URL`. OpenAPI 3.1.
- **Descriptions**: every operation has `summary` and `description`, every parameter and response field a description. These are written for the LLM and edited only in code. The tool descriptions:
  - **`search_products`**: *"Find gift ideas across the whole shop by the shopper's constraints: who it is for (recipient), the occasion, a budget (min_price / max_price), a delivery deadline (max_shipping_days), gift wrap. This is the default tool for gift requests ('something for my sister's new flat, about €50'). There is no free-text search: moods and tastes ('cosy', 'she loves music') are for you to judge from the returned names, tags and subcategories. Returns up to 15 compact summaries, best rated first; narrow the filters rather than paging. 'outside_price_range' tells you when matching products exist just outside the budget. If nothing matches, 'suggestions' says which constraint to relax. Call get_product_details on the 2–3 you intend to recommend. With no filters at all it returns the shop's best-rated products."*
  - **`get_products_by_category`**: *"List the products in one category, optionally narrowed by subcategory, price, recipient, occasion, delivery deadline or gift wrap. Use it when the shopper names a kind of product: 'a chef's knife' (subcategory Knives), 'something for the kitchen', 'your candles'. For gift requests defined by recipient, occasion or budget, use search_products instead. Use subcategory for a specific product type, so 'outside_price_range' tells you about that type only. Products with 'also_listed_in' appear in two categories: never recommend both listings."*
  - **`get_categories`**: *"List the shop's 11 categories with product counts, price ranges, subcategories and how many in-stock products suit each occasion. Use it when the shopper asks what the shop sells, or to pick a valid category and subcategory before get_products_by_category. Not needed before search_products. Call it at most once per conversation."*
  - **`get_product_details`**: *"Get the full record for one product: description, materials, colour, gift wrap, shipping time and availability. Call it for each of the 2–3 products before recommending them (in parallel), and whenever the shopper asks about a specific item. The description is what makes a good reason."*

### Observability

- One JSON log line per request: operation, status, latency, result count, `error.code`, and the key fingerprint (the first 6 hex characters of its SHA-256).
- `GET /health` returns `{"status": "ok", "products_loaded": 152, "catalog_loaded_at": "..."}`.

## Rules

1. The raw CSV is never modified. A bad export fails the build; a bad `catalog.json` fails startup.
2. The committed `catalog.json` always equals a fresh build.
3. Lists exclude out-of-stock products unless asked for.
4. Search never returns a product twice. Cross-listed products always carry `also_listed_in`.
5. Every response stays within the response budget.
6. Every error uses the envelope, with a `hint` that names the next action.
7. No data endpoint works without a valid key.
8. `rating: null` means unrated, never 0.
9. Internal fields never appear in responses.
10. **API changes are additive only** (D3): new optional parameters, fields or operations. A breaking change takes two deploys with a Publish in between.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `CATALOG_API_KEYS` | required | Valid keys, comma-separated |
| `CATALOG_DATA_PATH` | `data/catalog.json` | Normalised catalogue |
| `PUBLIC_BASE_URL` | `http://localhost:8000` (required in prod) | `servers[0].url` |
| `RATE_LIMIT_PER_MINUTE` | `120` | Per key |
| `LOG_LEVEL` | `INFO` | |

## Deployment

The DigitalOcean droplet (D4) at `https://catalog.builtbykromha.com`. Steps are in `PLAYBOOK.md`.

```
indigo.ai ──HTTPS──▶ system Caddy (:443, automatic Let's Encrypt) ──HTTP──▶ catalog-service container (127.0.0.1:8000)
```

- **Files**: `deploy/` holds `docker-compose.yml` (the service only), `catalog.caddy` (the site block, imported by the system Caddyfile) and `.env.example`.
- **Container**: Uvicorn, one worker (the rate limiter is in memory), `--proxy-headers`, `restart: unless-stopped`.
- **Secrets**: `deploy/.env` on the droplet (`chmod 600`, git-ignored).
- **Firewall**: ports 22 (key-only), 80 and 443. Port 8000 is bound to loopback, never public.
- **Environments**: one deployment serves both the platform's Test and Production environments, separated by key (D3).

## Dependencies

- **indigo.ai platform** (consumer): a tool collection imported from the public `/openapi.json`, calling with `X-API-Key` from a workspace secret. Open platform questions are in `AGENT_SPEC.md`.
- **Client CSV export** (input): static file. The facts it relies on are in `docs/reference/catalog-data-profile.md`.

## Acceptance criteria

- All four tools can be called from the indigo.ai agent.
- **Build**:
  - 152 rows become 152 records, and two runs give identical output.
  - The report lists 6 category fixes, 2 cross-listed pairs, and `C` and `m`.
- **Categories**: `get_categories` returns 11 categories whose counts sum to 152. Home & Living has `in_stock_by_occasion.housewarming = 18`.
- **Browse**:
  - `"Home and Living"` resolves to `home-living` and includes `HL-013`. The default page returns 15 of `total: 26` with `next_offset: 15`.
  - `home-living` with `occasion=housewarming`, €40–60 includes `HL-024` with `also_listed_in` pointing to `KD-023`.
  - `kitchen-dining` with `subcategory=Knives`, `max_price=100` returns `KD-002` and `KD-003`, with `outside_price_range.above_max = {count: 1, min_price_eur: 149}`.
  - `best_rated` puts `TG-006` first in Tech & Gadgets.
- **Search**:
  - `occasion=housewarming`, €40–60 returns 13 products, without the duplicate tumbler set.
  - `recipient=kids` returns only `KI-*` products.
  - No filters returns the best-rated in-stock products: `TG-006` first, `total: 139`.
- **Errors**:
  - `electronics` returns `found: false`, `category_not_found` and `did_you_mean: ["tech-gadgets"]`.
  - `XX-999` returns `found: false` and `product_not_found`.
  - An empty result returns at least one suggestion.
- **Auth**:
  - No data endpoint works without a valid key, and a removed key gets `401` after restart.
  - The 121st request in a minute gets `429`.
- **Budget**: `limit=25` serialises under 2.6k tokens (characters / 3.6), and summaries expose neither `stock` nor `rating_score`.
- **OpenAPI**:
  - Every operation, parameter and field has a description, and there are no header parameters (enforced by tests).
  - On the deployed service, `/openapi.json`, `/docs` and `/redoc` return `200` without a key, and `servers[0].url` is the public URL.

## Decisions

Reasoning in `archive/catalog-spec-decisions.md`.

| # | Decision | Status |
|---|---|---|
| D1 | Static API key in `X-API-Key`, several keys, rate limit (`AUTHENTICATION.md`) | Accepted |
| D2 | Recoverable errors return `200` + `found: false` | Accepted |
| D3 | One deployment for both platform environments; additive API changes | Accepted |
| D4 | DigitalOcean VPS behind Caddy | Accepted |
| D5 | Narrow keyword `query` | Superseded by D6 |
| D6 | Browse-first, three tools | Superseded by D7 |
| D7 | Four tools: filters-only search, response budget | Accepted |
