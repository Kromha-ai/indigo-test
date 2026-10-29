---
Status: Draft
Last updated: 2026-10-29
---

# Spec: Catalog Service

## Purpose

Turn the client's CSV catalogue export into a small, authenticated HTTP API whose OpenAPI specification becomes the agent's tool collection on the indigo.ai platform. The consumer is an LLM-driven gift assistant (`docs/specs/AGENT_SPEC.md`), not a human developer. Every design choice below starts from that consumer: it has a finite context window, it reads tool and parameter descriptions literally, and it recovers from errors only if the error tells it how.

Context: `docs/reference/scenario.md`. Data findings: `docs/reference/catalog-data-profile.md`.

## Goals

1. Expose the catalogue through exactly three tools, `get_categories`, `get_products_by_category` and `get_product_details`, and show that they cover the conversations (decision D6).
2. Produce an OpenAPI document that loads cleanly into an indigo.ai tool collection, with every operation and parameter described for an LLM reader.
3. Protect every data endpoint with an API key.
4. Keep every response bounded in size, whatever the query.
5. Turn every unhappy path into a response the agent can act on.

## Out of scope

- Writing back to the catalogue (orders, carts, stock reservations). The service is read-only.
- A database. 152 rows load into memory at startup in milliseconds; a database would add operational cost with no benefit at this size.
- Free-text, keyword or semantic search. At 152 products the agent browses filtered categories and does the matching itself (decision D6). Revisit if the catalogue grows by an order of magnitude.
- Product images and storefront URLs: the export has neither.
- Multi-language catalogue content. Data stays in English; the agent handles the shopper's language.
- Admin UI and hot-reloading. A new export means rebuild (`build_catalog`), review the diff and report, then redeploy.

## Stack

| Concern | Choice | Reason |
|---|---|---|
| Language | Python 3.12 | |
| Framework | FastAPI + Pydantic v2 | Required by the brief; generates the OpenAPI document from the same models that validate responses |
| Server | Uvicorn | |
| Dependency management | `uv` (`pyproject.toml` + `uv.lock`) | Fast, reproducible |
| Tests | `pytest` + FastAPI `TestClient` (httpx) | Tests run at the HTTP boundary, the same place the platform calls |
| Lint/format | `ruff` | |
| Container | Single `Dockerfile` | Any host that runs a container can deploy it |

Code lives in `catalog-service/` (see its `CLAUDE.md`). At runtime the service reads only the normalised catalogue (`CATALOG_DATA_PATH`, default `data/catalog.json`), never the raw CSV.

## Data model

### Build pipeline

The raw export is never modified. A build step reads it and writes a normalised, enriched catalogue, and the service loads that catalogue. All cleaning and enrichment happens in that one reviewable place, and at startup the service only parses clean JSON.

```
raw_data/gift-shop-catalog.csv            (client export, read-only)
        │   catalog-service/catalog_build/build_catalog.py
        │   + catalog_build/synonyms.toml           (category synonyms for did_you_mean)
        ▼
catalog-service/data/catalog.json         (what the service loads)
catalog-service/data/catalog.normalized.csv   (same records, flat, for humans and the client)
catalog-service/data/BUILD_REPORT.md      (every fix applied, per row, plus build statistics)
```

- **Command**: `uv run python -m catalog_build.build_catalog` (from `catalog-service/`).
- **Deterministic**: the same input and mapping files always give byte-identical output (sorted keys, fixed float rounding, records ordered by `product_id`, no timestamps in the data files). Only `BUILD_REPORT.md` carries the build date and the SHA-256 of the source CSV.
- **Committed**: the three outputs are committed. A new export then shows up as a reviewable diff of the clean data, and the report is what gets shown to the client ("here is what we fixed in your export"). A test rebuilds in memory and fails if the committed `catalog.json` is stale.
- **Fails loudly**: the build aborts, and writes nothing, if a row has an unparseable price, stock or shipping value, a category that does not normalise, or an unknown recipient or occasion.
- **Load-time check**: the service validates `catalog.json` against the Pydantic record model at startup and refuses to start if it does not match, so a hand-edited or truncated file is never half-served.
- **Raw CSV in the image**: not needed. The Docker image ships `data/catalog.json` only.

### Normalisation rules

| Raw | Rule | Finding |
|---|---|---|
| `category` | Trim, lowercase, replace ` and ` with ` & `, then map to the canonical name. Unknown values abort the build | 17 spellings, 11 categories |
| `subcategory`, `brand`, `name`, `color`, `material` | Trim. Empty becomes `null` | |
| `price_eur` | Parse as decimal, rounded to 2 decimals | |
| `stock` | Int. Kept in the file (needed to derive `availability`), never exposed by the API | `999` sentinel, `0` = out of stock |
| `rating`, `reviews_count` | Empty becomes `null`. Never coerced to 0 | 5 unrated products |
| `recipient` | Enum: `her`, `him`, `couple`, `kids`, `anyone` | |
| `occasion`, `tags` | Split on `|`, trim, lowercase, drop empties. An empty field gives `[]` | |
| `gift_wrap` | `yes` gives `true`, `no` gives `false` | |
| `shipping_days` | Int. `0` means digital, instant delivery | Gift cards |

### Normalised record

One record per raw row. Columns marked *derived* do not exist in the export.

| Field | Type | Derived | Purpose |
|---|---|---|---|
| `product_id` | string | | Key |
| `name`, `brand`, `description` | string | | |
| `category`, `category_slug` | string | slug | Canonical display name, and the API identifier (`home-living`) |
| `subcategory`, `subcategory_slug` | string | slug | |
| `price_eur` | number | | |
| `stock` | int | | Internal only |
| `availability` | enum | yes | `in_stock`, `low_stock` (1–5), `out_of_stock`. A band instead of a count stops the agent reciting warehouse numbers, and hides the `999` sentinel |
| `rating`, `reviews_count` | number / int, nullable | | As published. Null means unrated |
| `is_rated` | bool | yes | |
| `rating_score` | number | yes | Weighted rating for ranking (below) |
| `recipient` | enum | | As published |
| `recipients_match` | list | yes | Every recipient filter value this product satisfies (below) |
| `occasions`, `tags` | list | | |
| `color`, `material` | string, nullable | | |
| `gift_wrap` | bool | | |
| `shipping_days` | int | | |
| `is_digital` | bool | yes | `shipping_days = 0` |
| `also_listed_in` | list | yes | Other listings of the same product: `{product_id, category_slug}`. Empty unless cross-listed |

### Derived fields

#### `rating_score`: rating weighted by review count

A 4.8 from 12 reviews should not outrank a 4.7 from 842. `rating_score` is a Bayesian average that pulls each rating toward the catalogue mean, more strongly when there are few reviews:

```
rating_score = (v / (v + m)) · R  +  (m / (v + m)) · C
  R = product rating, v = its reviews_count
  C = mean rating of all rated products (currently 4.37)
  m = 25th percentile of reviews_count (currently 96)
```

- `C` and `m` are computed at build time from the export and recorded in `BUILD_REPORT.md`, so they follow the data rather than being hard-coded.
- **Unrated products** get `rating_score = C`, so they are neither rewarded nor punished in ranking. Their `rating` stays `null` and the agent never presents them as rated.
- `rating_score` is a ranking key only. It is **not exposed** in the API: an opaque 4.61 is a number the agent would be tempted to quote. Responses show `rating` and `reviews_count`.
- With the current data, the top of the ranking is the E-Reader (4.8 from 923 reviews), the Ember Candle (4.8 from 431) and the Chef's Knife (4.8 from 394), which matches intuition.

#### `recipients_match`: recipient wildcard, resolved once

The recipient rule (see *Filter semantics*) is applied at build time, so the runtime filter is plain list membership:

| `recipient` | `recipients_match` |
|---|---|
| `her` | `her` |
| `him` | `him` |
| `couple` | `couple` |
| `kids` | `kids` |
| `anyone` | `anyone`, `her`, `him`, `couple`. **Never** `kids` |

#### Cross-listed products

Two products appear twice under different IDs (`HL-021`/`KD-024`, `HL-024`/`KD-023`). The build detects duplicates by an exact match on (`name`, `brand`, `price_eur`, `description`) and links each listing to the other through `also_listed_in`.

- Both IDs resolve in `get_product_details`.
- `get_products_by_category` shows each listing in its own category, because a shopper browsing Kitchen & Dining should see the tumbler set.
- Every summary of a cross-listed product carries `also_listed_in`. An agent browsing both Home & Living and Kitchen & Dining therefore sees that the two tumbler sets are one product, and never recommends both.

### Product representations

**`ProductSummary`** is what category browsing returns. It carries enough for the agent to judge fit on its own (*"which of these is cosy?"*) while staying around 75 tokens per item:

```json
{
  "product_id": "HL-003",
  "name": "Ember Ceramic Candle",
  "subcategory": "Candles",
  "brand": "Fold Studio",
  "price_eur": 42.00,
  "rating": 4.8,
  "reviews_count": 431,
  "availability": "in_stock",
  "recipient": "anyone",
  "occasions": ["thank-you", "birthday", "christmas"],
  "tags": ["candle", "scented", "woody", "refillable"],
  "shipping_days": 2
}
```

- `tags` are included because, without a search engine, they are the agent's best matching signal after the name. Measured cost: +18% tokens (the largest category goes from ~1,950 to ~2,300).
- `shipping_days` is included because delivery time often decides between two candidates (*"it ships in two days"*).
- `also_listed_in` appears only on the cross-listed products, e.g. `"also_listed_in": [{"product_id": "KD-023", "category_slug": "kitchen-dining"}]`.
- The category is not repeated per item: the response states it once.

**`ProductDetail`** contains every field of the summary, plus `category`, `description`, `color`, `material`, `gift_wrap`, `is_digital` and `also_listed_in` (always present, possibly empty). Internal fields (`stock`, `rating_score`, `recipients_match`) are never serialised.

The description is excluded from lists on purpose. The agent shortlists from summaries, then fetches detail for the two or three it intends to recommend, and the description is what it uses to say *why*.

## API surface

Base path is `/`. All responses are `application/json`. Every operation has a stable `operationId` equal to its tool name. The platform uses it as the tool identifier.

| Tool (`operationId`) | Method and path | Auth |
|---|---|---|
| `get_categories` | `GET /categories` | API key |
| `get_products_by_category` | `GET /categories/{category}/products` | API key |
| `get_product_details` | `GET /products/{product_id}` | API key |
| *(not a tool)* | `GET /health` | none |
| *(not a tool)* | `GET /openapi.json`, `GET /docs`, `GET /redoc` (public API documentation) | none |

### Tools

#### `get_categories`

No parameters. Returns all 11 categories. The payload is small enough to need no pagination (about 1k tokens).

```json
{
  "categories": [
    {
      "slug": "home-living",
      "name": "Home & Living",
      "product_count": 28,
      "in_stock_count": 26,
      "price_range_eur": {"min": 28.00, "max": 249.00},
      "subcategories": ["Candles", "Decor", "Fragrance", "Garden", "Lighting", "Storage", "Textiles", "Vases"],
      "in_stock_by_occasion": {"housewarming": 18, "thank-you": 9, "christmas": 6, "anniversary": 5, "birthday": 4, "graduation": 1}
    }
  ]
}
```

This is the agent's map for choosing which categories to browse:

- Subcategories let it narrow a browse in one step.
- `in_stock_by_occasion` tells it where the gifts for an occasion actually are. Housewarming gifts span five categories, and this shows which ones are worth a call.

#### `get_products_by_category`

Browse one category, narrowed by the shopper's constraints. The agent calls it for the one to three most relevant categories, in parallel when there are several.

| Param | In | Type | Default | Constraint |
|---|---|---|---|---|
| `category` | path | string | required | Slug or display name, case-insensitive |
| `subcategory` | query | string | none | Case-insensitive exact match. Use for a specific product type (*"a chef's knife"* → Knives) |
| `min_price` | query | number | none | ≥ 0 |
| `max_price` | query | number | none | ≥ 0, ≥ `min_price` |
| `recipient` | query | enum | none | See *Filter semantics* |
| `occasion` | query | enum | none | |
| `max_shipping_days` | query | int | none | 0–14. Use when the shopper has a deadline |
| `gift_wrap` | query | bool | none | `true` keeps only wrappable products |
| `include_out_of_stock` | query | bool | `false` | |
| `sort` | query | enum | `best_rated` | `best_rated`, `price_asc`, `price_desc` |
| `limit` | query | int | `30` | 1–30. The largest category has 28 products, so any category fits in one call |
| `offset` | query | int | `0` | ≥ 0 |

Response: `ListResponse` (below).

**`best_rated`** sorts by `rating_score` descending, so ratings with few reviews count for less and unrated products sit at the catalogue mean.

#### `get_product_details`

| Param | In | Type | Constraint |
|---|---|---|---|
| `product_id` | path | string | Case-insensitive, trimmed. `hl-003` resolves to `HL-003` |

Response: `{"found": true, "product": ProductDetail}`. Out-of-stock products are still returned, with `availability: out_of_stock`, because the shopper may ask about one by name.

### `ListResponse`

```json
{
  "found": true,
  "category": {"slug": "kitchen-dining", "name": "Kitchen & Dining"},
  "items": [ProductSummary],
  "total": 2,
  "returned": 2,
  "offset": 0,
  "next_offset": null,
  "applied_filters": {"subcategory": "Knives", "max_price": 100},
  "outside_price_range": {"above_max": {"count": 1, "min_price_eur": 149.00}},
  "suggestions": []
}
```

- `total` is the match count before pagination. `next_offset` is `null` on the last page.
- `applied_filters` echoes the normalised filters (`"Home and Living"` becomes `"home-living"`), so the agent can see how it was understood.
- `outside_price_range` appears when a price filter is set. It counts the products that match **every other filter** but fall outside the price band: `above_max` and/or `below_min`, each with `count` and the nearest price. This is how the agent learns that what the shopper asked for exists just over budget. *"A chef's knife under €100"* browsed as `subcategory=Knives, max_price=100` returns the paring knife and the sharpening stone, plus `above_max: {count: 1, min_price_eur: 149}`: the chef's knife. Without the subcategory, the same browse over all of Kitchen & Dining says *"5 more from €115"*, which is true but not useful, which is why specific product types are browsed by subcategory.
- `suggestions` appears when the result is empty (see *Empty results*).

**Size bound**: a full page of 30 summaries with tags is about 2,700 tokens. No single response from this service exceeds about 3k tokens. A typical turn browses one to three filtered categories, about 1–4k tokens in total.

### Filter semantics

- **Recipient**: `her`, `him` and `couple` match products tagged with that value **or** `anyone`. `kids` matches only `kids`. The `anyone` bucket includes chef's knives and fragrances, which are not children's gifts. `anyone` matches only `anyone`. Resolved at build time into `recipients_match`; the runtime check is membership.
- **Occasion**: matches when the value is in the product's `occasions`. Products with no occasions never match an occasion filter.
- **Price**: inclusive on both ends.
- **Out of stock**: excluded by default from every list. The agent must not recommend what cannot be bought; it can opt in to answer "do you have X?".
- **Enums** (`recipient`, `occasion`, `sort`) are declared as OpenAPI enums, so the model sees the valid vocabulary in the tool schema itself.

### Empty results

A filter combination that matches nothing returns **`200`**, not `404`, with `items: []` and a `suggestions` array computed by relaxing one constraint at a time:

```json
{
  "items": [],
  "total": 0,
  "suggestions": [
    {"change": "raise max_price to 25", "would_match": 4},
    {"change": "remove occasion filter", "would_match": 7},
    {"change": "set include_out_of_stock=true", "would_match": 1}
  ]
}
```

Relaxations tried: drop `occasion`, drop `recipient`, drop `subcategory`, drop `max_shipping_days`, drop `gift_wrap`, widen the price band to the nearest price that yields a match, include out of stock. Only relaxations that produce at least one match are returned, ordered by `would_match` descending, capped at 3. This gives the agent something concrete to tell the shopper ("nothing under €20 for a housewarming, but there are four things under €25").

### Errors

Errors come in two kinds, and both use the same `error` envelope (decision D2):

- **Recoverable**: the agent asked for something that does not exist (unknown category, subcategory or product). These return **`200`** with `"found": false` and the envelope, so the model sees the recovery hints whatever the platform does with 4xx bodies.
- **Failures**: bad key, invalid parameters, rate limit, server error. These keep their real HTTP status with the envelope as the body.

```json
{
  "found": false,
  "error": {
    "code": "category_not_found",
    "message": "No category matches 'electronics'.",
    "hint": "Use one of the slugs in 'did_you_mean', or call get_categories for the full list.",
    "did_you_mean": ["tech-gadgets"],
    "valid_values": ["home-living", "kitchen-dining", "tech-gadgets", "..."]
  }
}
```

| Code | HTTP | When | Recovery content |
|---|---|---|---|
| `unauthorized` | 401 | Missing or wrong API key | `hint` names the header |
| `category_not_found` | 200, `found: false` | Unknown category | `did_you_mean` (fuzzy match on slug and name, plus a synonym table: *electronics* and *gadgets* map to `tech-gadgets`, *beauty* and *skincare* to `beauty-wellness`, *toys* to `kids`, *travel* to `outdoor-travel`...), plus `valid_values` |
| `subcategory_not_found` | 200, `found: false` | Subcategory not in that category | `valid_values` = that category's subcategories, `did_you_mean` if another category has it |
| `product_not_found` | 200, `found: false` | Unknown product ID | `hint` to browse with `get_products_by_category`; `did_you_mean` for IDs one edit away |
| `invalid_parameter` | 422 | Validation failure | Plain-language message per field ("max_price (20) must be greater than or equal to min_price (50)"), replacing FastAPI's default validation body |
| `rate_limited` | 429 | Over the per-key rate limit | `hint` to retry after `Retry-After` seconds |
| `internal_error` | 500 | Unexpected | Generic message, no stack trace |

**Success responses carry `"found": true`** on `get_products_by_category` (as part of `ListResponse`) and `get_product_details` (`{"found": true, "product": {...}}`), so the agent always checks one field. `get_categories` cannot hit a not-found case and does not carry it. An empty result is still `found: true` with `items: []` and `suggestions`: the category exists, nothing in it matches.

**Accepted cost**: if the platform hides 4xx bodies, the model gets a generic failure for `invalid_parameter`. These are agent mistakes, not shopper situations; tool descriptions, enums and evals are what prevent them. The Phase 1 spike still records what the platform does with 4xx, for the README.

### Authentication

The full caller guide, platform setup, rotation and the decision record are in `AUTHENTICATION.md` (repo root). Contract summary:

- **Scheme**: static API key in `X-API-Key`, HTTPS only. `/health`, `/openapi.json`, `/docs` and `/redoc` are open.
- **Keys**: `CATALOG_API_KEYS`, comma-separated, one key per consumer and environment, compared with `secrets.compare_digest`. The service refuses to start with an empty list.
- **OpenAPI**: declared as an `apiKey` security scheme only. Never as a header parameter, because the platform would show it to the LLM.
- **Rate limit**: 120 requests per minute per key fingerprint, in memory. Over it, `429 rate_limited` with `Retry-After`.

### OpenAPI document

The OpenAPI document is the product. Requirements:

- `info.description` explains, in a paragraph, what the catalogue is and when to use each tool.
- Every operation has `operationId`, a `summary`, and a `description` written for an LLM: what it returns, when to call it, when **not** to call it (pointing to the better tool), and one example.
- Every parameter has a description, its default, its constraints and an example.
- Every response model field has a description, especially the non-obvious ones: `availability`, `is_digital`, the `suggestions` array, `recipient` wildcard semantics.
- **Published at a public URL.** The deployed service serves the document at `https://catalog.builtbykromha.com/openapi.json`, with Swagger UI at `/docs` and ReDoc at `/redoc`. These are FastAPI's defaults; the requirements are that they stay switched on in production and stay public:
  - `openapi_url`, `docs_url` and `redoc_url` keep their defaults in every environment. They are never set to `None` "for production".
  - Auth is a dependency on the data routers, **not** a middleware or an app-wide dependency, so the documentation routes never require a key. A test calls all three without a key and expects `200`.
  - `servers[0].url` equals `PUBLIC_BASE_URL`, so the published document names its real host and **Try it out** in `/docs` calls the deployed service.
  - The URL is listed in `README.md` and `AUTHENTICATION.md` once deployed.
- **Imported from the public URL.** The indigo.ai tool collection imports the document straight from `https://catalog.builtbykromha.com/openapi.json`. The live endpoint is the single source; there is no exported or committed copy. The public URL is therefore part of the contract: if it breaks, the platform cannot refresh the tools.
- **Self-contained.** The document must not depend on anything external; FastAPI's `#/components` `$ref`s are internal and fine.
- **`servers`** is set from `PUBLIC_BASE_URL` for the published document and `/docs`. The platform ignores it and uses the collection's **Endpoint** fields instead.
- **Form editing.** Operations using `$ref` or `anyOf` show as read-only in the platform's form but work as defined. That is intended: descriptions are edited in code, never in the platform.
- **OpenAPI 3.1**, as FastAPI emits it. The platform's importer accepts 3.1 (confirmed 2026-10-29), so no 3.0 conversion is needed.

Draft tool descriptions (to be refined against real agent transcripts):

- **`get_categories`**: *"List the shop's 11 categories with product counts, price ranges, subcategories and how many in-stock products suit each occasion. Call this first for any gift request, to decide which one to three categories to browse. Example: for a housewarming gift, browse the categories with the most housewarming products. It does not change during a conversation, so call it once."*
- **`get_products_by_category`**: *"List the products in one category as compact summaries (name, subcategory, price, rating, availability, recipient, occasions, tags, shipping days), narrowed by the shopper's constraints: price, recipient, occasion, delivery deadline (max_shipping_days), gift wrap. Use subcategory for a specific product type ('a chef's knife' → subcategory Knives). When a request could fit several categories, call this for each of them in parallel. Choose the products yourself from what comes back: moods and tastes like 'cosy' or 'she loves music' are judged from names, tags and subcategories. Out-of-stock items are excluded unless include_out_of_stock=true. 'outside_price_range' tells you when matching products exist just outside the budget: tell the shopper rather than hiding them. If nothing matches, 'suggestions' says which constraint to relax. Products with 'also_listed_in' appear in two categories: never recommend both listings."*
- **`get_product_details`**: *"Get the full record for one product: description, materials, colour, gift wrap, shipping time and availability. Call it for each of the 2–3 products before recommending them (in parallel), and whenever the shopper asks about a specific item. The description is what makes a good reason."*

### Observability

- One structured JSON log line per request: method, path, operation, status, latency, result count, and the API key's fingerprint (first 6 chars of its SHA-256), never the key itself.
- `GET /health` returns `{"status": "ok", "products_loaded": 152, "catalog_loaded_at": "..."}`.

## Business rules and invariants

1. The raw CSV is never modified. All cleaning and enrichment happens in the build step, and its outputs are committed.
2. A bad export fails the build, and a catalogue file that fails validation fails startup. Nothing is ever half-served.
3. The committed `catalog.json` always equals a fresh build of the committed CSV and mapping files (enforced by a test).
4. Lists never include out-of-stock products unless the caller opts in.
5. Every listing of a cross-listed product says so (`also_listed_in`), in summaries and details.
6. No response exceeds the documented page size (`limit` ≤ 30).
7. Every error is in the envelope, with a `hint` that names the next action.
8. No data endpoint is reachable without a valid API key.
9. `rating: null` means unrated. It is never reported or ranked as 0; for ranking, unrated products take the catalogue mean via `rating_score`.
10. Internal fields (`stock`, `rating_score`, `recipients_match`) never appear in API responses.

## Configuration

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `CATALOG_API_KEYS` | yes | none | Comma-separated valid keys |
| `CATALOG_DATA_PATH` | no | `data/catalog.json` | Normalised catalogue produced by the build step |
| `PUBLIC_BASE_URL` | no (yes in prod) | `http://localhost:8000` | `servers[0].url` in the published OpenAPI document and `/docs` (the platform ignores it) |
| `RATE_LIMIT_PER_MINUTE` | no | `120` | Per-key request limit |
| `LOG_LEVEL` | no | `INFO` | |

## Deployment

On the developer's DigitalOcean VPS (decision D4) at **`https://catalog.builtbykromha.com`**, behind a reverse proxy that terminates HTTPS. The droplet is dedicated to this service: nothing else runs on it, and no other proxy holds ports 80 and 443.

```
indigo.ai ──HTTPS──▶ Caddy (:443, automatic Let's Encrypt) ──HTTP──▶ catalog-service container (127.0.0.1:8000)
```

- **Files**: `deploy/` at the repo root holds `docker-compose.yml` (service + Caddy), `Caddyfile`, and `.env.example`. The compose file builds the image from `catalog-service/`.
- **TLS**: Caddy obtains and renews the Let's Encrypt certificate automatically. The service's DNS name is **`catalog.builtbykromha.com`**, with an A record pointing at the droplet.
- **Container**: Uvicorn, one worker (the in-memory rate limiter assumes a single process), `restart: unless-stopped`, port bound to `127.0.0.1` only, so the service is reachable only through Caddy. Uvicorn runs with `--proxy-headers` so redirects and `/docs` see the HTTPS scheme.
- **Secrets**: `deploy/.env` on the droplet only (`chmod 600`, owned by the deploy user, git-ignored). Holds `CATALOG_API_KEYS` and `PUBLIC_BASE_URL`.
- **Firewall**: DigitalOcean Cloud Firewall or `ufw` allows only 22 (SSH, key-only), 80 (ACME challenge and redirect to HTTPS) and 443.
- **Deploy**: on the droplet, `git pull` then `docker compose -f deploy/docker-compose.yml up -d --build`. The catalogue is baked into the image, so a data rebuild is deployed the same way.
- **Logs**: `docker compose logs`. JSON lines from the service, Caddy access logs. Request headers are not logged, so keys never reach the logs (only fingerprints, from the service).
- **Health**: `GET /health` through the public URL after every deploy (`PLAYBOOK.md`, *Deploying*).

## Inter-service dependencies

| Dependency | Direction | Notes |
|---|---|---|
| indigo.ai platform | Consumer | A tool collection imported from the public `/openapi.json`; calls tools with `X-API-Key` from a workspace secret. Remaining unknowns are in `AGENT_SPEC.md`, *Still to verify in Phase 1* |
| Client CSV export | Input | Static file; schema assumptions are in `docs/reference/catalog-data-profile.md` |

## Acceptance criteria

- All three tools are callable from the indigo.ai agent with the API key configured on the platform side.
- The build turns 152 raw rows into 152 records, and running it twice gives byte-identical `catalog.json`.
- `BUILD_REPORT.md` lists the 6 category fixes, the 2 cross-listed pairs, and the derived constants `C` and `m`.
- `get_categories` reports exactly 11 categories, the counts sum to 152, and Home & Living reports `in_stock_by_occasion.housewarming = 18`.
- `get_products_by_category("Home and Living")` resolves to `home-living`, includes `HL-013`, and returns all 26 in-stock products in one call.
- `get_products_by_category("home-living", occasion=housewarming, min_price=40, max_price=60)` includes `HL-024` with `also_listed_in` pointing to `KD-023`.
- `get_products_by_category("kids")` returns only `KI-*` products; `recipient=kids` on any other category returns nothing (with `suggestions`).
- `sort=best_rated` ranks the E-Reader (`TG-006`) first in Tech & Gadgets.
- `get_products_by_category("kitchen-dining", subcategory="Knives", max_price=100)` returns `KD-002` and `KD-003`, with `outside_price_range.above_max = {count: 1, min_price_eur: 149}`.
- Summaries carry `tags`, and no summary exposes `stock` or `rating_score`.
- Unknown category `electronics` returns `200` with `found: false`, `category_not_found` and `did_you_mean: ["tech-gadgets"]`.
- Unknown product `XX-999` returns `200` with `found: false` and `product_not_found`; a known ID returns `found: true` and `product`.
- An empty filter result returns `200` with at least one actionable suggestion.
- No request without a valid key reaches a data endpoint; a key removed from `CATALOG_API_KEYS` gets `401` straight after restart.
- The 121st request within a minute on one key gets `429 rate_limited`.
- `/openapi.json` declares no header parameters (enforced by a test).
- Every operation and parameter in `/openapi.json` has a non-empty description, enforced by a test.
- On the deployed service, `/openapi.json`, `/docs` and `/redoc` answer `200` without a key, and `servers[0].url` is the public HTTPS URL.

## Decision log

Decisions that are not obvious from the contract above, kept short enough to explain in a sentence each. Status: `Proposed` (recommended, waiting for sign-off), `Accepted`, `Superseded by Dn`. A decision is recorded here unless it needs its own document, in which case this index points to it.

| # | Decision | Status | Record |
|---|---|---|---|
| D1 | Authentication scheme | Accepted | `AUTHENTICATION.md` |
| D2 | Recoverable errors return `200` + `found: false` | Accepted | Below |
| D3 | One deployment for both platform environments | Accepted | Below |
| D4 | Hosting on a DigitalOcean VPS | Accepted | Below |
| D5 | Narrow keyword `query` with no dead end | Superseded by D6 | Below |
| D6 | Browse-first with three tools, no search | Accepted | Below |

### D2: Recoverable errors return `200` with `found: false`

**Status**: Accepted · 2026-10-29

**Context**: the agent can only recover from an unknown category or product ID if it reads `did_you_mean` and `hint`. It is not known whether indigo.ai passes 4xx response bodies to the model or replaces them with a generic tool failure.

**Options**: (a) HTTP-correct `404` with the envelope, and verify the platform behaviour first; (b) `200` with `found: false` and the same envelope.

**Decision**: (b) for the recoverable not-found cases. Real failures (`401`, `422`, `400`, `429`, `500`) keep their HTTP status.

**Consequences**: recovery works whatever the platform does with 4xx, and Phase 1 no longer depends on that spike. The API is less REST-pure: monitoring must count `found: false` responses as a metric, since they are not errors at the HTTP level. They are logged with their `error.code`.

**Revisit if**: a consumer other than an LLM agent appears, or the platform is confirmed to pass 4xx bodies and REST semantics start to matter.

### D3: One deployment serves both platform environments

**Status**: Accepted · 2026-10-29

**Context**: indigo.ai tool collections have a Test and a Production endpoint. The catalogue is read-only and identical in both environments.

**Options**: (a) one deployment, both endpoints pointing at it, separated by keys (`platform-test`, `platform-prod`); (b) separate staging and production deployments.

**Decision**: (a). A second deployment would cost a host and a second set of secrets without protecting any data.

**Consequences**: a deploy changes the API under the Production agent *before* its tool collection is re-imported and published. Therefore:

- Changes are **additive only**: new optional parameters, new fields, new operations.
- Never rename or remove a parameter, field or operation, and never tighten a constraint, in a single deploy.
- A breaking change takes two deploys, the first adding the new form alongside the old one, with a Publish in between.

Revisit if a breaking change is unavoidable, or if a consumer other than the platform appears.

### D4: Hosting on a DigitalOcean VPS

**Status**: Accepted · 2026-10-29

**Context**: the service must be on public HTTPS, and it is called during live conversations, so a slow first response hurts the shopper. Managed hosts considered: Render, Railway, Fly.io, Cloud Run. Their free tiers sleep or scale to zero, and the first request after idling can take 30–60 s, which may exceed the platform's tool-call timeout.

**Decision**: the developer's existing DigitalOcean VPS (droplet), dedicated to this service, at `catalog.builtbykromha.com`. The container runs with Docker Compose behind **Caddy** for automatic HTTPS.

**Consequences**:

- Always on: no cold starts, so the tool-call timeout no longer constrains hosting (it is still measured, for the README).
- No extra hosting cost.
- We own TLS, the firewall, OS updates and restarts. Caddy and `restart: unless-stopped` cover most of it; the rest is in `PLAYBOOK.md`.
- A DNS name is required for the certificate.
- Single instance: if the droplet is down, the assistant cannot recommend anything. Acceptable for this scope.

**Revisit if** traffic needs more than one instance (the in-memory rate limiter would then need a shared store), or if the droplet's other workloads start competing for resources.

### D5: Narrow keyword `query` with no dead end

**Status**: Superseded by D6 · 2026-10-29

**Context**: a test of 60 typical shopper words against the catalogue, using the first draft rules (exact tokens plus plural strip), showed two clear groups:

- **Concrete product nouns worked**: knife, candle, coffee, necklace, blanket, headphones.
- **Interests and moods missed entirely**: cosy, pamper, spa, music, gaming, gardening, jewelry, puppy all found 0 products. Near forms missed too (`plants` did not find the planter, `cooking` found only a cookbook).
- **Descriptions and category names produced false positives**: `cat` matched a diffuser, and `smart home` matched 36 products.

A synonym table fixes these one at a time and never ends. Meanwhile the catalogue is small: the structured filters cut it to 10–25 summaries, and the model can tell which of them are "cosy" far better than any keyword engine.

**Options**:

- **(A)** Narrow and harden the keyword search: product words only, any-word matching with the agent expanding synonyms, stem, prefix and typo matching, descriptions and category names left out of the index, and no dead end.
- **(B)** A plus semantic search with local embeddings.
- **(C)** Drop `query`, filters only.

**Decision**: (A). It keeps the case keyword search is good at, a concrete product lookup with `near_misses`. It fixes the measured near-form misses, and it stops an unmatched query from emptying a filtered result. (B) was rejected for now: about 150 MB of model, a similarity cut-off to tune, and harder to test. Semantic search always returns *something*, which looks like relevance when it is not.

**Consequences**:

- Understanding moods and interests moves to the agent, through the filters and its own judgement. The tool description and system prompt must teach this: filters first, concrete words, several alternatives.
- Results carry `query_matched` / `query_note`, so the agent knows when the query was ignored.
- This has to be **proven by the evals** (E15–E17 in `AGENT_SPEC.md`), not assumed.

**Revisit if** the vague-word evals fail after tuning the description and prompt. The fallback is **(C)**: remove `query`, keep the filters, and let the agent browse summaries. Losing the direct product lookup is acceptable at this catalogue size, and `near_misses` would then come from a `subcategory` filter instead.

### D6: Browse-first with three tools, no search

**Status**: Accepted · 2026-10-29 · supersedes D5

**Context**: D5 kept a keyword `query` on a fourth tool, `search_products`, and hardened it. The same test that motivated D5 showed that the hard cases (*"cosy"*, *"she loves music"*, *"a pamper gift"*) are meaning, not words, and that the catalogue is small enough for the model to read:

| | In-stock products | Summary tokens |
|---|---|---|
| Largest category (Home & Living) | 26 | ~2,000 (~2,300 with tags) |
| Typical category | 10–20 | 700–1,600 |
| Whole in-stock catalogue | 140 | ~10,600 |

The platform calls tools in parallel, so browsing several categories costs one round trip.

**Options**:

- **(A)** Keep D5: `search_products` with a hardened keyword `query`.
- **(B)** Browse-first with `search_products` kept as filters only, no `query`, for cross-category requests.
- **(C)** Browse-first with three tools: `get_categories` → `get_products_by_category` (one to three categories, in parallel) → `get_product_details`.

**Decision**: (C).

- The model does the matching over full, filtered lists, which beats any keyword engine on moods and tastes.
- Three tools with distinct jobs leave no "which tool?" ambiguity. (B) brings that ambiguity back for a convenience that parallel category calls already give.
- It removes relevance scoring, matching rules, `query_matched`, `near_misses` and the `interests` vocabulary: less to build, test and explain.

**Consequences**:

- **Removed**: `search_products`, `query`, `search_weights`, `near_misses`, `interests` (and `interests.toml`), `search_too_broad`, `listing_group`.
- **Added**:
  - in summaries: `tags`, and `also_listed_in` on cross-listed products;
  - in `get_categories`: `in_stock_by_occasion`;
  - in category lists: `outside_price_range`, which replaces `near_misses`;
  - `max_shipping_days` and `gift_wrap` filters on category browsing;
  - the page limit raised to 30, so any category fits in one call.
- **Cross-category requests rely on the agent choosing categories well.** `in_stock_by_occasion` and the subcategory lists are its map, and the prompt tells it to browse the two or three most relevant categories in parallel.
- **Over-budget cases rely on browsing by subcategory** for a specific product type, so that `outside_price_range` is specific.
- **The evals have to prove it**: E1 (spans categories), E3 (over budget), and E15–E17 (moods and tastes).

**Revisit if** the catalogue grows past a few hundred products (a category would no longer fit in one call), or the evals show the agent regularly missing the best category for cross-category requests. The first step would then be option (B).
