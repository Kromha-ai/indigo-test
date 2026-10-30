# Gift Shop Catalog Service and Gift Assistant

A product discovery assistant for an online gift shop. Shoppers describe who a gift is for and roughly what they want; the assistant asks at most a couple of questions and recommends two or three products, each with a reason.

The shop's only data was a CSV export of its catalogue. This repository turns it into an authenticated API whose OpenAPI document is imported as tools by the assistant on the indigo.ai platform.

| | |
|---|---|
| Live assistant | *added in Phase 4* |
| API base URL | `https://catalog.builtbykromha.com` |
| OpenAPI document (public) | [`/openapi.json`](https://catalog.builtbykromha.com/openapi.json) · Swagger UI [`/docs`](https://catalog.builtbykromha.com/docs) · ReDoc [`/redoc`](https://catalog.builtbykromha.com/redoc) |
| Authentication | `X-API-Key` header on every data endpoint. See [`AUTHENTICATION.md`](AUTHENTICATION.md) |

## The tools

The assistant gets four tools, one job each:

| Tool | Route | When the assistant uses it |
|---|---|---|
| `search_products` | `GET /products/search` | The default for gift requests: filters by recipient, occasion, budget, delivery deadline and gift wrap across the whole shop, one result per product. With no filters, the best-rated products |
| `get_products_by_category` | `GET /categories/{category}/products` | The shopper names a kind of product ("a chef's knife", "your candles"), optionally down to a subcategory |
| `get_product_details` | `GET /products/{product_id}` | The full record, including the description that makes a good reason, for the 2–3 products about to be recommended |
| `get_categories` | `GET /categories` | "What do you sell?", and the valid categories and subcategories |

Every list response is compact and bounded: 10 summaries by default, at most 25, about 1k–2.5k tokens, with no descriptions. When the budget excludes something relevant, `outside_price_range` says so (for example *"1 more Knives product, from €149"*). When nothing matches, `suggestions` names the one constraint to relax. An unknown category or product ID returns `found: false` with `did_you_mean`, so the assistant can correct itself.

## Try it

You need an API key; keys are issued by the service operator.

```bash
curl -s -H "X-API-Key: $KEY" \
  "https://catalog.builtbykromha.com/products/search?recipient=her&occasion=housewarming&min_price=40&max_price=60"
```

Or open [`/docs`](https://catalog.builtbykromha.com/docs), select **Authorize**, enter the key, and try any operation.

## How it is built

```
raw_data/gift-shop-catalog.csv          client export, never edited
        │  catalog_build/  (normalise, flag duplicates, weight ratings)
        ▼
catalog-service/data/catalog.json       committed, deterministic, validated at startup
        │  FastAPI service, in memory
        ▼
https://catalog.builtbykromha.com       Docker on a DigitalOcean droplet, behind Caddy (HTTPS)
        │  OpenAPI import
        ▼
indigo.ai tool collection  →  gift assistant
```

- **The data is cleaned once, at build time.** The export has 17 spellings of 11 categories, two products listed twice under different IDs, out-of-stock items, unrated products and sentinel stock values. The build fixes or flags each of them and lists every fix in `catalog-service/data/BUILD_REPORT.md`. Details: [`docs/reference/catalog-data-profile.md`](docs/reference/catalog-data-profile.md).
- **Ratings are weighted by review count** for ranking, so a 4.8 from a dozen reviews does not outrank a 4.7 from hundreds.
- **There is no free-text search, on purpose.** Keyword matching was tested against typical shopper words and failed on exactly the words that matter ("cosy", "pamper", "music"). Filters narrow the list, and the assistant judges taste from the summaries.

## Run it locally

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/); Docker is optional.

```bash
cd catalog-service
uv sync
cp .local.env.example .local.env          # then set CATALOG_API_KEYS
uv run uvicorn app.main:create_app --factory --env-file .local.env --reload
uv run pytest                             # 136 tests, no network or secrets needed
```

Daily workflow, rebuilding the catalogue, deploying and rolling back: [`PLAYBOOK.md`](PLAYBOOK.md).

## Repository map

| Path | What it holds |
|---|---|
| `catalog-service/` | The FastAPI service, the catalogue build step, the generated data and the tests |
| `deploy/` | Docker Compose for the droplet and the Caddy site block |
| `raw_data/` | The client's export, as received |
| `docs/specs/` | The contracts: [`CATALOG_SPEC.md`](docs/specs/CATALOG_SPEC.md) (the API) and [`AGENT_SPEC.md`](docs/specs/AGENT_SPEC.md) (the assistant's behaviour and evaluation) |
| `docs/reference/` | [The client's problem](docs/reference/scenario.md) and [what the data really contains](docs/reference/catalog-data-profile.md) |
| `docs/guides/` | [Testing](docs/guides/testing.md) and [secrets management](docs/guides/secrets-management.md) |
| `docs/planning/` | [The roadmap](docs/planning/ROADMAP.md) |
| `archive/` | Why things are the way they are, every decision with the options considered: [the API](archive/catalog-spec-decisions.md) and [the assistant](archive/agent-spec-decisions.md) |
| [`AUTHENTICATION.md`](AUTHENTICATION.md) | How callers authenticate, and why this scheme |
| [`WORKFLOW.md`](WORKFLOW.md) | How the project is run: spec first, then plan, then code |

## The assistant

*Written in Phase 5, from `docs/specs/AGENT_SPEC.md` and `agent/`.*

### The prompt

### How the tools are bound to the agent

### Conversation design decisions

- How many questions before recommending, and why
- The recommendation message: products per message, fields, format, next step
- The hard cases: vague, specific, over budget, nothing suitable, out of stock, off-topic
