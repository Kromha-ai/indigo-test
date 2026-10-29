---
Status: Draft
Last updated: 2026-10-29
---

# Spec: Catalog Service

## Purpose

Turn the client's CSV catalogue export into a small, authenticated HTTP API whose OpenAPI specification becomes the agent's tool collection on the indigo.ai platform. The consumer is an LLM-driven gift assistant (`docs/specs/AGENT_SPEC.md`), not a human developer. Every design choice below starts from that consumer: it has a finite context window, it reads tool and parameter descriptions literally, and it recovers from errors only if the error tells it how.

Context: `docs/reference/scenario.md`. Data findings: `docs/reference/catalog-data-profile.md`.

## Goals

1. Expose the catalogue through at least `get_categories`, `get_products_by_category` and `get_product_details`, plus the additions justified in *Tools*.
2. Produce an OpenAPI document that loads cleanly into an indigo.ai tool collection, with every operation and parameter described for an LLM reader.
3. Protect every data endpoint with an API key.
4. Keep every response bounded in size, whatever the query.
5. Turn every unhappy path into a response the agent can act on.

## Out of scope

- Writing back to the catalogue (orders, carts, stock reservations). The service is read-only.
- A database. 152 rows load into memory at startup in milliseconds; a database would add operational cost with no benefit at this size.
- Semantic or embedding search. Keyword scoring over name, tags, subcategory and description is enough for 152 short records. Revisit if the catalogue grows by an order of magnitude.
- Product images and storefront URLs: the export has neither. **Open with client**: whether a product URL pattern exists (non-blocking).
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
        │   + catalog_build/interests.toml          (subcategory/tag → interest mapping)
        │   + catalog_build/synonyms.toml           (category and query synonyms)
        ▼
catalog-service/data/catalog.json         (what the service loads)
catalog-service/data/catalog.normalized.csv   (same records, flat, for humans and the client)
catalog-service/data/BUILD_REPORT.md      (every fix applied, per row, plus build statistics)
```

- **Command**: `uv run python -m catalog_build.build_catalog` (from `catalog-service/`).
- **Deterministic**: the same input and mapping files always give byte-identical output (sorted keys, fixed float rounding, records ordered by `product_id`, no timestamps in the data files). Only `BUILD_REPORT.md` carries the build date and the SHA-256 of the source CSV.
- **Committed**: the three outputs are committed. A new export then shows up as a reviewable diff of the clean data, and the report is what gets shown to the client ("here is what we fixed in your export"). A test rebuilds in memory and fails if the committed `catalog.json` is stale.
- **Fails loudly**: the build aborts, and writes nothing, if a row has an unparseable price, stock or shipping value, a category that does not normalise, an unknown recipient or occasion, or a subcategory with no interest mapping.
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
| `review_volume` | enum | yes | `none`, `few` (<50), `some` (50–199), `many` (200+). Lets the agent say "loved by hundreds of reviewers" without quoting a number |
| `recipient` | enum | | As published |
| `recipients_match` | list | yes | Every recipient filter value this product satisfies (below) |
| `occasions`, `tags` | list | | |
| `interests` | list | yes | Controlled interest vocabulary (below) |
| `color`, `material` | string, nullable | | |
| `gift_wrap` | bool | | |
| `shipping_days` | int | | |
| `is_digital` | bool | yes | `shipping_days = 0` |
| `listing_group` | string | yes | `product_id` of the primary listing. Equal to `product_id` unless cross-listed |
| `is_primary_listing` | bool | yes | |
| `also_listed_in` | list | yes | Other listings of the same product: `{product_id, category_slug}` |
| `search_weights` | map token → weight | yes | Precomputed keyword index (below). Not in the CSV view |

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
- `rating_score` is a ranking key only. It is **not exposed** in the API: an opaque 4.61 is a number the agent would be tempted to quote. Responses show `rating`, `reviews_count` and `review_volume`.
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

#### `interests`: what the recipient is into

Shoppers describe people by interests (*"she loves cooking"*, *"he's into music"*), while the export describes products by subcategory and free tags (380 tags, mostly used once). `interests` bridges the two with a small controlled vocabulary. It is exposed as an enum filter, so the agent picks from a list instead of guessing keywords.

Vocabulary (19): `home-decor`, `cooking`, `entertaining`, `coffee-tea`, `drinks`, `tech`, `music-audio`, `reading`, `writing-stationery`, `art-craft`, `games-puzzles`, `wellness`, `fitness`, `outdoors-travel`, `plants-gardening`, `jewellery-style`, `pets`, `photography`, `kids-play`.

The mapping lives in `catalog_catalog_build/interests.toml`. Every subcategory must map to at least one interest; Gift Cards is the one explicit exception (it maps to none). Tag rules can add interests on top of the subcategory, e.g. tag `travel` adds `outdoors-travel`, `retro` or `gaming` add `games-puzzles`, `drawing` adds `art-craft`, `plant` adds `plants-gardening`. The draft subcategory mapping:

| Interest | Subcategories |
|---|---|
| `home-decor` | Candles, Decor, Lighting, Storage, Textiles, Vases, Fragrance (Home & Living) |
| `cooking` | Cookware, Knives, Serving, Tableware |
| `entertaining` | Bar, Serving, Tableware |
| `coffee-tea` | Coffee, Tea |
| `drinks` | Bar |
| `tech` | Audio, Creative, Desk, Home Tech, Mobile, Photo, Reading, Wearable |
| `music-audio` | Audio |
| `reading` | Books, Reading |
| `writing-stationery` | Paper, Pens |
| `art-craft` | Craft |
| `games-puzzles` | Board Games, Classic Games, Puzzles |
| `wellness` | Bath, Fragrance (Beauty & Wellness), Grooming, Recovery, Skincare, Sleep |
| `fitness` | Fitness, Recovery |
| `outdoors-travel` | Bags, Drinkware, Outdoor |
| `plants-gardening` | Garden |
| `jewellery-style` | Bracelets, Earrings, Necklaces, Rings, Watches |
| `pets` | Cats, Dogs |
| `photography` | Photo |
| `kids-play` | Toys, plus every product in Kids |

`BUILD_REPORT.md` lists the product count per interest, so a thin or overloaded interest is visible at review time.

#### `search_weights`: precomputed keyword index

Each record carries a map from normalised token to weight, so a query is scored by summing the weights of its tokens.

- **Normalisation**: lowercase, strip accents, split on non-alphanumerics, drop a short stopword list, light plural strip (`candles` → `candle`, `knives` → `knife`).
- **Field weights**: name ×3, tags ×3, interests ×2, subcategory ×2, brand ×2, category ×1, description ×1. A token in several fields gets the highest weight, not the sum, so long descriptions cannot outscore names.
- **Query side**: `catalog_catalog_build/synonyms.toml` expands query tokens before scoring (`kitchen` → `cooking`, `tea` → `coffee-tea`, `music` → `music-audio`, `jewelry` → `jewellery`...). The same file holds the category synonyms used for `did_you_mean`.

#### Cross-listed products

Two products appear twice under different IDs (`HL-021`/`KD-024`, `HL-024`/`KD-023`). The build detects duplicates by an exact match on (`name`, `brand`, `price_eur`, `description`). The listing with the lexicographically lowest ID is primary, and every listing gets the same `listing_group`.

- Both IDs resolve in `get_product_details`, and each response carries `also_listed_in`.
- `get_products_by_category` shows each listing in its own category, because a shopper browsing Kitchen & Dining should see the tumbler set.
- `search_products` returns one result per `listing_group` (the primary), so a cross-category result never recommends the same thing twice.

### Product representations

**`ProductSummary`** is used in lists and kept deliberately small, at roughly 60 tokens per item:

```json
{
  "product_id": "HL-003",
  "name": "Ember Ceramic Candle",
  "category": "home-living",
  "subcategory": "Candles",
  "brand": "Fold Studio",
  "price_eur": 42.00,
  "rating": 4.8,
  "reviews_count": 431,
  "review_volume": "many",
  "availability": "in_stock",
  "recipient": "anyone",
  "occasions": ["thank-you", "birthday", "christmas"],
  "shipping_days": 2
}
```

`shipping_days` is in the summary, not only in the detail, because delivery time is often what decides between two candidates (*"it ships in two days"*). It costs about 4 tokens per item.

**`ProductDetail`** contains every field of the summary, plus `description`, `tags`, `interests`, `color`, `material`, `gift_wrap`, `is_digital` and `also_listed_in`. Internal fields (`stock`, `rating_score`, `recipients_match`, `listing_group`, `search_weights`) are never serialised.

The description is excluded from lists on purpose. The agent shortlists from summaries, then fetches detail for the two or three it intends to recommend, and the description is what it uses to say *why*.

## API surface

Base path is `/`. All responses are `application/json`. Every operation has a stable `operationId` equal to its tool name. The platform uses it as the tool identifier.

| Tool (`operationId`) | Method and path | Auth |
|---|---|---|
| `get_categories` | `GET /categories` | API key |
| `get_products_by_category` | `GET /categories/{category}/products` | API key |
| `search_products` | `GET /products/search` | API key |
| `get_product_details` | `GET /products/{product_id}` | API key |
| *(not a tool)* | `GET /health` | none |
| *(not a tool)* | `GET /openapi.json`, `GET /docs`, `GET /redoc` (public API documentation) | none |

`/products/search` is declared before `/products/{product_id}` so that `search` is never captured as an ID.

### Tools

#### `get_categories`

No parameters. Returns all 11 categories. The payload is small enough to need no pagination.

```json
{
  "categories": [
    {
      "slug": "home-living",
      "name": "Home & Living",
      "product_count": 28,
      "in_stock_count": 26,
      "price_range_eur": {"min": 28.00, "max": 249.00},
      "subcategories": ["Candles", "Decor", "Fragrance", "Garden", "Lighting", "Storage", "Textiles", "Vases"]
    }
  ]
}
```

Subcategories are included so the agent can narrow a browse in one step without a separate tool.

#### `get_products_by_category`

Browse one category.

| Param | In | Type | Default | Constraint |
|---|---|---|---|---|
| `category` | path | string | required | Slug or display name, case-insensitive |
| `subcategory` | query | string | none | Case-insensitive exact match |
| `min_price` | query | number | none | ≥ 0 |
| `max_price` | query | number | none | ≥ 0, ≥ `min_price` |
| `recipient` | query | enum | none | See *Filter semantics* |
| `occasion` | query | enum | none | |
| `interest` | query | enum | none | See *Derived fields* → `interests` |
| `include_out_of_stock` | query | bool | `false` | |
| `sort` | query | enum | `best_rated` | `best_rated`, `price_asc`, `price_desc` |
| `limit` | query | int | `10` | 1–25 |
| `offset` | query | int | `0` | ≥ 0 |

Response: `ListResponse` (below).

#### `search_products` (added)

Search across all categories by constraints and free text.

**Why it was added:** the conversation this assistant exists for (*"something for my sister, she just moved into a new flat, maybe fifty euros"*) is defined by recipient, occasion and budget, not by category. Housewarming gifts span Home & Living, Kitchen & Dining, Tech & Gadgets, Books and gift cards. With only category browsing, the agent has to guess categories, fetch several of them and filter in its head. That burns context, costs several tool round trips, and lets it miss the best match in a category it did not think of. One search call with structured filters answers the question directly.

| Param | Type | Default | Constraint / meaning |
|---|---|---|---|
| `query` | string | none | Free text, 1–100 chars. Matched against name, tags, subcategory, brand and description |
| `category` | string | none | Optional narrowing, same rules as the path param above |
| `min_price`, `max_price` | number | none | As above |
| `recipient` | enum | none | |
| `occasion` | enum | none | |
| `interest` | enum | none | What the recipient is into. Prefer this to `query` when one of the 19 values fits |
| `max_shipping_days` | int | none | 0–14. Use when the shopper has a deadline |
| `gift_wrap` | bool | none | `true` keeps only wrappable products |
| `include_out_of_stock` | bool | `false` | |
| `sort` | enum | `relevance` if `query` is set, else `best_rated` | `relevance`, `best_rated`, `price_asc`, `price_desc` |
| `limit` | int | `10` | 1–25 |
| `offset` | int | `0` | |

At least one parameter besides `sort`/`limit`/`offset` must be set. An unconstrained search would just be a full catalogue dump and returns `400 search_too_broad`.

**Relevance scoring**: the query is normalised the same way as the index and expanded with `synonyms.toml`. Each product's score is the sum of its `search_weights` for the query tokens (see *Derived fields*). Products scoring 0 are dropped when `query` is set. Ties break on `rating_score`, then `product_id`.

**`best_rated`** sorts by `rating_score` descending, so ratings with few reviews count for less and unrated products sit at the catalogue mean.

#### `get_product_details`

| Param | In | Type | Constraint |
|---|---|---|---|
| `product_id` | path | string | Case-insensitive, trimmed. `hl-003` resolves to `HL-003` |

Response: `ProductDetail`. Out-of-stock products are still returned, with `availability: out_of_stock`, because the shopper may ask about one by name.

### `ListResponse`

```json
{
  "items": [ProductSummary],
  "total": 13,
  "returned": 10,
  "offset": 0,
  "next_offset": 10,
  "applied_filters": {"occasion": "housewarming", "min_price": 40, "max_price": 60},
  "suggestions": [],
  "near_misses": []
}
```

- `total` is the match count before pagination. `next_offset` is `null` on the last page.
- `applied_filters` echoes the normalised filters, for example `category: "Home and Living"` becomes `"home-living"`, so the agent can see how it was understood.
- `suggestions` appears when the result is empty (see *Empty results*).
- `near_misses` (`search_products` only): when a `query` is set, the best-matching products that were excluded **only** by the price filter. At most 2 `ProductSummary` items, ranked by relevance, and only those that score at least as well as the top returned result. Otherwise it is empty.

  **Why it was added**: *"a chef's knife under €100"* returns the €69 paring knife, but the only chef's knife costs €149. Without `near_misses`, the agent cannot tell the shopper that what they asked for exists just over budget, and it ends up presenting a different product as if it were the answer.

**Size bound**: the default page of 10 summaries is around 600–800 tokens and the hard maximum of 25 is around 2,000. No single response from this service can exceed about 2.5k tokens.

### Filter semantics

- **Recipient**: `her`, `him` and `couple` match products tagged with that value **or** `anyone`. `kids` matches only `kids`. The `anyone` bucket includes chef's knives and fragrances, which are not children's gifts. `anyone` matches only `anyone`. Resolved at build time into `recipients_match`; the runtime check is membership.
- **Interest**: matches when the value is in the product's `interests`.
- **Occasion**: matches when the value is in the product's `occasions`. Products with no occasions never match an occasion filter.
- **Price**: inclusive on both ends.
- **Out of stock**: excluded by default from every list. The agent must not recommend what cannot be bought; it can opt in to answer "do you have X?".
- **Enums** (`recipient`, `occasion`, `interest`, `sort`) are declared as OpenAPI enums, so the model sees the valid vocabulary in the tool schema itself.

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

Relaxations tried: drop `occasion`, drop `recipient`, drop `interest`, drop `subcategory`, drop `max_shipping_days`, drop `gift_wrap`, widen the price band to the nearest price that yields a match, include out of stock, drop `query`. Only relaxations that produce at least one match are returned, ordered by `would_match` descending, capped at 3. This gives the agent something concrete to tell the shopper ("nothing under €20 for a housewarming, but there are four things under €25").

### Errors

Every non-2xx response uses one envelope:

```json
{
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
| `category_not_found` | 404 | Unknown category | `did_you_mean` (fuzzy match on slug and name, plus a synonym table: *electronics* and *gadgets* map to `tech-gadgets`, *beauty* and *skincare* to `beauty-wellness`, *toys* to `kids`, *travel* to `outdoor-travel`...), plus `valid_values` |
| `subcategory_not_found` | 404 | Subcategory not in that category | `valid_values` = that category's subcategories, `did_you_mean` if another category has it |
| `product_not_found` | 404 | Unknown product ID | `hint` to use `search_products`; `did_you_mean` for IDs one edit away |
| `invalid_parameter` | 422 | Validation failure | Plain-language message per field ("max_price (20) must be greater than or equal to min_price (50)"), replacing FastAPI's default validation body |
| `search_too_broad` | 400 | `search_products` with no constraint | `hint` to add a query or filter |
| `rate_limited` | 429 | Over the per-key rate limit | `hint` to retry after `Retry-After` seconds |
| `internal_error` | 500 | Unexpected | Generic message, no stack trace |

**Risk, verify in Phase 1**: it is not yet confirmed whether the indigo.ai platform passes 4xx response bodies to the model or replaces them with a generic tool failure. If it hides them, the not-found cases switch to `200` with `{"found": false, "error": {...}}`, keeping the same envelope. Because the envelope is the same either way, the switch is a single response-builder change.

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
- **Published at a public URL.** The deployed service serves the document at `https://<host>/openapi.json`, with Swagger UI at `/docs` and ReDoc at `/redoc`. These are FastAPI's defaults; the requirements are that they stay switched on in production and stay public:
  - `openapi_url`, `docs_url` and `redoc_url` keep their defaults in every environment. They are never set to `None` "for production".
  - Auth is a dependency on the data routers, **not** a middleware or an app-wide dependency, so the documentation routes never require a key. A test calls all three without a key and expects `200`.
  - `servers[0].url` equals `PUBLIC_BASE_URL`, so the published document names its real host and **Try it out** in `/docs` calls the deployed service.
  - The URL is listed in `README.md` and `AUTHENTICATION.md` once deployed.
- **Imported from the public URL.** The indigo.ai tool collection imports the document straight from `https://<host>/openapi.json`. The live endpoint is the single source; there is no exported or committed copy. The public URL is therefore part of the contract: if it breaks, the platform cannot refresh the tools.
- **Self-contained.** The document must not depend on anything external; FastAPI's `#/components` `$ref`s are internal and fine.
- **`servers`** is set from `PUBLIC_BASE_URL` for the published document and `/docs`. The platform ignores it and uses the collection's **Endpoint** fields instead.
- **Form editing.** Operations using `$ref` or `anyOf` show as read-only in the platform's form but work as defined. That is intended: descriptions are edited in code, never in the platform.
- **Risk, verify in Phase 1**: FastAPI emits OpenAPI 3.1. If the platform's importer requires 3.0, generate a 3.0-compatible document (in particular, render `Optional` fields as `nullable: true` instead of `anyOf: [..., null]`).

Draft tool descriptions (to be refined against real agent transcripts):

- **`search_products`**: *"Find gift ideas across the whole catalogue by who it is for, the occasion, what they are into (interest), a budget, a delivery deadline and/or free text for a product type (e.g. 'chef's knife', 'cosy'). This is the default tool for recommendations. Returns compact summaries; call get_product_details on the 2–3 you intend to recommend. Out-of-stock items are excluded unless include_out_of_stock=true. If nothing matches, 'suggestions' says which constraint to relax. 'near_misses' lists strong matches that are just outside the price range: tell the shopper about them rather than hiding them."*
- **`get_categories`**: *"List the shop's product categories with product counts, price ranges and subcategories. Use when the shopper asks what the shop sells, or to pick a valid category before calling get_products_by_category. Not needed before search_products."*
- **`get_products_by_category`**: *"Browse the products in one category, optionally narrowed by subcategory, price, recipient or occasion. Use when the shopper names a kind of product ('show me your candles', 'something for the kitchen'). For open-ended gift requests use search_products instead."*
- **`get_product_details`**: *"Get the full record for one product: description, materials, colour, gift wrap, shipping time and availability. Call this for each product before recommending it, and whenever the shopper asks about a specific item."*

### Observability

- One structured JSON log line per request: method, path, operation, status, latency, result count, and the API key's fingerprint (first 6 chars of its SHA-256), never the key itself.
- `GET /health` returns `{"status": "ok", "products_loaded": 152, "catalog_loaded_at": "..."}`.

## Business rules and invariants

1. The raw CSV is never modified. All cleaning and enrichment happens in the build step, and its outputs are committed.
2. A bad export fails the build, and a catalogue file that fails validation fails startup. Nothing is ever half-served.
3. The committed `catalog.json` always equals a fresh build of the committed CSV and mapping files (enforced by a test).
4. Lists never include out-of-stock products unless the caller opts in.
5. `search_products` never returns the same physical product twice.
6. No response exceeds the documented page size (`limit` ≤ 25).
7. Every error is in the envelope, with a `hint` that names the next action.
8. No data endpoint is reachable without a valid API key.
9. `rating: null` means unrated. It is never reported or ranked as 0; for ranking, unrated products take the catalogue mean via `rating_score`.
10. Internal fields (`stock`, `rating_score`, `recipients_match`, `listing_group`, `search_weights`) never appear in API responses.

## Configuration

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `CATALOG_API_KEYS` | yes | none | Comma-separated valid keys |
| `CATALOG_DATA_PATH` | no | `data/catalog.json` | Normalised catalogue produced by the build step |
| `PUBLIC_BASE_URL` | no (yes in prod) | `http://localhost:8000` | `servers[0].url` in the published OpenAPI document and `/docs` (the platform ignores it) |
| `RATE_LIMIT_PER_MINUTE` | no | `120` | Per-key request limit |
| `LOG_LEVEL` | no | `INFO` | |

## Deployment

The service needs to be on public HTTPS so the platform can call it. Any container host will do.

**Recommendation**: Render or Railway web service from the Dockerfile, single instance, environment variables set in the host's dashboard. Cold-start latency on a free tier must be checked against the platform's tool timeout. If it is a problem, use the smallest paid instance or an uptime ping. **Decision needed by Phase 4** (non-blocking before then).

## Inter-service dependencies

| Dependency | Direction | Notes |
|---|---|---|
| indigo.ai platform | Consumer | A tool collection imported from the public `/openapi.json`; calls tools with `X-API-Key` from a workspace secret. Remaining unknowns are in `AGENT_SPEC.md`, *Still to verify in Phase 1* |
| Client CSV export | Input | Static file; schema assumptions are in `docs/reference/catalog-data-profile.md` |

## Acceptance criteria

- All four tools are callable from the indigo.ai agent with the API key configured on the platform side.
- The build turns 152 raw rows into 152 records, and running it twice gives byte-identical `catalog.json`.
- `BUILD_REPORT.md` lists the 6 category fixes, the 2 cross-listed pairs, and the derived constants `C` and `m`.
- Every subcategory except Gift Cards has at least one interest.
- `get_categories` reports exactly 11 categories and the counts sum to 152.
- `get_products_by_category("Home and Living")` resolves to `home-living` and includes `HL-013`.
- `search_products(occasion=housewarming, min_price=40, max_price=60)` returns 13 products, with no duplicate tumbler set.
- `search_products(recipient=kids)` returns only `KI-*` products.
- `search_products(interest=coffee-tea)` returns the in-stock Coffee and Tea products.
- `sort=best_rated` ranks the E-Reader (`TG-006`) first.
- `search_products(query="chef's knife", max_price=100)` returns in-budget knife products, and `near_misses` contains `KD-001` (€149).
- Unknown category `electronics` returns `category_not_found` with `did_you_mean: ["tech-gadgets"]`.
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
| D1 | Authentication scheme | Proposed | `AUTHENTICATION.md` |
