# Catalog Service — Workspace

A product discovery assistant for an online gift shop. The client's CSV catalogue export becomes an authenticated FastAPI service whose OpenAPI specification becomes a tool collection for a gift assistant agent on the indigo.ai platform. Context: `docs/reference/scenario.md`.

## Projects in this workspace

- `catalog-service/`: FastAPI service exposing the catalogue as agent tools (Python 3.12, uv, pytest).
- `agent/`: version-controlled record of the indigo.ai configuration: Global Agent Settings, the Gift Assistant and General Agent blocks, greeting, tool setup, simulations (`simulations.csv`), custom evaluator prompts and the guardrails' Control Room rules (`quality.md`) and dated runs (`evals.md`). Created in roadmap Phase 4.
- `deploy/`: Docker Compose for the service and the Caddy site block (`catalog.caddy`) imported by the droplet's system Caddy (decision D4).
- `raw_data/`: the client's export, as received. **Never edit it.** All cleaning and enrichment happens in the build step (`catalog-service/catalog_build/`), which writes the normalised catalogue to `catalog-service/data/`.

Each project has its own `CLAUDE.md` with stack-specific commands and conventions.

---

## Operations

`AUTHENTICATION.md` explains how callers authenticate (header, keys per environment, platform secret, rotation) and records the authentication decision. Read it before touching auth.

`PLAYBOOK.md` covers first-time setup, daily workflow, running tests, and deploying. The service has no database: it loads the normalised `catalog-service/data/catalog.json` into memory at startup.

---

## Documentation index

`docs/` holds all living documents, organised into four subfolders. Read the relevant document before making decisions about the API contract, data normalisation, or agent behaviour. When a roadmap is completed, it moves to `archive/` for historical reference.

| Folder | Purpose |
|---|---|
| `docs/planning/` | Roadmaps and tracking artifacts |
| `docs/specs/` | Service and agent specifications |
| `docs/guides/` | How-to guides and testing conventions |
| `docs/reference/` | Client context and data facts |

### planning

| Document | When to use it |
|---|---|
| `docs/planning/ROADMAP.md` | Active roadmap: five phases from walking skeleton to handover, plus two bonus phases (site widget, model comparison). Open it to see what is next and tick tasks off. |

### specs

| Document | When to use it |
|---|---|
| `docs/specs/CATALOG_SPEC.md` | Catalog Service contract (the reasoning lives in `archive/catalog-spec-decisions.md`): build step and normalisation rules, the four tools, parameters, response shapes, the response budget, error envelope, auth, OpenAPI requirements, acceptance criteria. |
| `docs/specs/AGENT_SPEC.md` | Gift assistant: architecture (a specialised Gift Assistant agent with the tools, plus the customised General Agent as fallback), Agent Block mapping and settings, conversation flows (what it can and cannot do, flowchart, data per flow), persona, conversation flow, mapping shopper language to tool parameters, hard rules, platform unknowns, the question rule, message format, hard-case handling, evaluation (scenarios E1–E18 as platform simulations, guardrails, evaluators). Reasoning in `archive/agent-spec-decisions.md`. |

### guides

| Document | When to use it |
|---|---|
| `docs/guides/testing.md` | How to run and write tests for the service, and how to run and record agent evals. |
| `docs/guides/secrets-management.md` | API key inventory, generation, storage, platform alignment and rotation. Read before the first deployment. |

### reference

| Document | When to use it |
|---|---|
| `docs/reference/scenario.md` | The client's problem, what the service and the assistant must do, and what gets handed over. Start here. |
| `docs/reference/catalog-data-profile.md` | What the CSV actually contains: columns, defects, cross-listings, out-of-stock items, reference queries. Every normalisation rule traces back here. |

### Archive

`archive/` contains completed roadmaps. Do not treat these as current. Reference them only to understand past decisions.

| Document | Notes |
|---|---|
| `archive/agent-spec-decisions.md` | Reasoning behind the agent spec (A1: evaluation in three layers). The spec is the source of truth |
| `archive/catalog-spec-decisions.md` | Reasoning behind the Catalog spec (D2–D7, including superseded D5 and D6), moved out of the spec on 2026-10-29. The spec is the source of truth |

---

## Domain glossary

- **Product**: one row of the catalogue, identified by `product_id` (`^[A-Z]{2}-\d{3}$`; the prefix encodes the category).
- **Category / subcategory**: 11 canonical categories, addressed in the API by slug (`home-living`), with 48 subcategories. The raw CSV has 17 spellings of the 11.
- **Cross-listed product**: one physical product listed twice under two IDs and categories (`HL-021`/`KD-024`, `HL-024`/`KD-023`). The lower ID is primary.
- **Recipient**: `her`, `him`, `couple`, `kids`, `anyone`. `anyone` is a wildcard for adults only.
- **Occasion**: `birthday`, `thank-you`, `christmas`, `housewarming`, `anniversary`, `graduation`.
- **Availability**: `in_stock`, `low_stock` (1–5 units), `out_of_stock`. Derived from stock; raw counts are not exposed.
- **Normalised catalogue**: `catalog-service/data/catalog.json`, built from the raw CSV by `build_catalog`. Committed, deterministic, and the only file the service reads. `BUILD_REPORT.md` beside it lists every fix applied.
- **Tool choice** (decision D7): `search_products` (filters only, across categories) for gift requests defined by recipient, occasion, budget or deadline; `get_products_by_category` when the shopper names a kind of product; `get_product_details` for the 2–3 products about to be recommended; `get_categories` for "what do you sell?". There is no free-text search.
- **`rating_score`**: rating weighted by review count (Bayesian average), used only for ranking (`sort=best_rated`), never shown.
- **Digital product**: `shipping_days = 0`. Currently only the gift cards (`EX-001`, `EX-002`).
- **Tool collection / operation**: on the indigo.ai platform, a tool collection is imported from the service's public `/openapi.json`. Each API operation becomes an action the agent can call, named by its `operationId`.
- **Test / Production**: platform environments. Tool collection edits reach Production only on workspace Publish; secrets hold one value per environment.
- **Shortlist**: the 2–3 products the assistant recommends in one turn.

---

## User roles

- **Shopper**: the end user in the site widget, who talks only to the assistant.
- **Assistant (agent)**: the LLM on the indigo.ai platform. It is the only caller of the Catalog Service.
- **Client**: the shop operator. Owns the catalogue export and receives the handover.
- **Developer**: builds and operates the service and the agent. The only one who commits (see `WORKFLOW.md`).

---

## Critical business rules

1. The raw CSV is never modified. A row that cannot be normalised fails the build; an invalid `catalog.json` fails startup. The committed `catalog.json` must match a fresh build.
2. The assistant never states a product, price, rating or availability that did not come from a tool response in that conversation.
3. Out-of-stock products are never recommended, and lists exclude them by default.
4. A product is never recommended twice. `search_products` returns one listing per product, and cross-listed products carry `also_listed_in` wherever they appear.
5. `recipient=kids` never matches `anyone` products (the `anyone` bucket includes knives).
6. Unrated means `null`, never `0`.
7. Every response stays within the spec's response budget (lists: 10 by default, at most 25 summaries, about 2.5k tokens; descriptions never in lists) and every error carries a `hint` the agent can act on.
8. Every data endpoint requires `X-API-Key` (`AUTHENTICATION.md`, decision D1). One key per consumer and environment. Keys never appear in the repo, logs or prompts; on the platform they live only in the `CATALOG_API_KEY` workspace secret.
9. Tool and parameter descriptions are part of the contract. They are edited in code, never in the platform form. Changing one means redeploying, re-importing the tool collection, re-running the evals and publishing.
