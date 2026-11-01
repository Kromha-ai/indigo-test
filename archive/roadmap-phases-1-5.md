# Roadmap: Catalog Service and Gift Assistant, phases 1–5

**Started**: 2026-10-29 · **Completed**: 2026-11-01
**Specs**: `docs/specs/CATALOG_SPEC.md` · `docs/specs/AGENT_SPEC.md`

Five phases, each a shippable slice. The optional sixth (site widget) continues in `docs/planning/ROADMAP.md`. Every phase ends with the service deployable and tests green.

The order is deliberate. Phase 1 puts a thin service on the real platform first, so that whatever the platform does differently from what the docs suggest is found before the full API is built.

---

## Status

| Phase | Goal | Status |
|---|---|---|
| 1 | Walking skeleton on the platform | Done |
| 2 | Browse and detail tools | Done |
| 3 | Search, recovery, and LLM-ready OpenAPI | Done |
| 4 | The assistant | Done 2026-11-01: NRT passes (runs 14–15), published, public link tested |
| 5 | Hardening and handover | Done 2026-11-01 |

---

## Phase 1: Walking skeleton on the platform

Goal: a deployed, authenticated service with `get_categories` bound as a tool on the indigo.ai platform, and the remaining platform unknowns answered.

- [x] Scaffold `catalog-service/`: `pyproject.toml` (uv), FastAPI app factory, settings from env, `ruff`, `pytest`
- [x] Build step `catalog_build/build_catalog.py`: every normalisation rule, derived fields (`availability`, `rating_score`, `recipients_match`, `listing_group`, `is_primary_listing`, `also_listed_in`), and fail-fast on bad rows
- [x] `catalog_build/synonyms.toml` (category synonyms for `did_you_mean`)
- [x] Generate `data/catalog.json`, `data/catalog.normalized.csv` and `data/BUILD_REPORT.md` (developer commits); review the report
- [x] Build tests against the real CSV: 152 records, 11 categories, the 6 drifted rows land in the right category, the 2 cross-listed pairs share a `listing_group` and point to each other in `also_listed_in`, 5 unrated products stay `null`, `kids` never in an `anyone` product's `recipients_match`
- [x] Build tests against small fixture CSVs: unknown category, bad price and unknown recipient abort the build; two runs give byte-identical output; committed `catalog.json` is not stale
- [x] `app/loader.py`: load and validate `catalog.json` at startup, refuse to start on a malformed file
- [x] Sign off the authentication decision in `AUTHENTICATION.md` (Accepted 2026-10-29)
- [x] `X-API-Key` auth dependency with multiple keys; refuse to start without keys; tests for missing, wrong and valid key
- [x] `GET /categories` (with subcategories and price ranges) and `GET /health`
- [x] `servers` populated from `PUBLIC_BASE_URL`
- [x] OpenAPI spec published: `/openapi.json`, `/docs`, `/redoc` left at FastAPI defaults; auth applied as a router dependency so they stay public; tests that all three answer `200` without a key and that `/openapi.json` declares no header parameters
- [x] Dockerfile (ships `data/catalog.json`), `.local.env.example`
- [x] `deploy/`: `docker-compose.yml` (service only, bound to `127.0.0.1`, one worker, `--proxy-headers`, `restart: unless-stopped`), `catalog.caddy` (site block imported by the droplet's system Caddy), `.env.example`
- [x] Droplet: DNS A record for `catalog.builtbykromha.com` (check it resolves first), Docker, clone to `/var/www/indigo-test`, `deploy/.env`, `docker compose up`, `import` the site block in `/etc/caddy/Caddyfile` and reload Caddy; smoke-test `https://catalog.builtbykromha.com/health`
- [x] Check the public spec URL on the deployed host (`PLAYBOOK.md`, *Every deploy*, step 2) and add it to `README.md` and `AUTHENTICATION.md`
- [x] Read the rest of the platform guide (*Getting Started*, *Build Your AI Agents*) in a signed-in browser; note the platform's vocabulary
- [x] Generate the three keys (`platform-test`, `platform-prod`, `local-dev`) and set `CATALOG_API_KEYS` in `deploy/.env` on the droplet
- [x] Set the `CATALOG_API_KEY` workspace secret on indigo.ai (Test and Production values) per `docs/guides/secrets-management.md`
- [x] Create the agent from zero in the sandbox workspace
- [x] Create the tool collection by importing a file of the OpenAPI document (`AGENT_SPEC.md`, *Tool binding procedure*), with the `X-API-Key` header from the secret
- [x] Assign the tools to the Gift Assistant and call `get_categories` from the Test chat; check the `platform-test` fingerprint in the service logs
- [x] Spike: check what the model sees on a 4xx (for the README; not blocking, see decision D2)
- [x] Spike: the tool-call timeout (measure with a deliberately slow test endpoint if undocumented; for the README, since the VPS has no cold starts) and how the public link works (which environment it serves)
- [x] Record the spike answers in `AGENT_SPEC.md` (*Observed on the platform*)
- [x] Mark `CATALOG_SPEC.md` **Approved**

## Phase 2: Browse and detail tools

Goal: `get_products_by_category` and `get_product_details` complete, with the full error envelope.

Prerequisite: Phase 1.

- [x] `ProductSummary` (with `tags`, `shipping_days`, `also_listed_in` on cross-listed products) and `ProductDetail` response models with field descriptions
- [x] Category resolution: slug, display name, case and whitespace insensitive, `and`/`&`
- [x] `GET /categories/{category}/products`: subcategory, price, recipient, occasion, `max_shipping_days`, `gift_wrap`, out-of-stock flag, `sort=best_rated` by `rating_score`, pagination (`limit` default 10, max 25), `ListResponse`
- [x] Recipient semantics: `her`/`him`/`couple` include `anyone`; `kids` exact
- [x] `GET /products/{product_id}`: case-insensitive ID, `also_listed_in`
- [x] Error envelope plus exception handlers; replace the default 422 body with plain-language `invalid_parameter` (built in Phase 1)
- [x] Tests for `invalid_parameter` once routes take parameters (e.g. `max_price` < `min_price`, `limit=0`)
- [x] `category_not_found` with fuzzy match and a synonym table; `subcategory_not_found`; `product_not_found` with near-ID suggestions, all as `200` + `found: false` (D2); `found: true` on success
- [x] HTTP-boundary tests for each tool, each error code, pagination edges (`offset` past the end, `limit` 1 and 25)
- [x] Redeploy (live at catalog.builtbykromha.com, 2026-10-29)
- [x] Re-import the tool collection from a fresh download of the OpenAPI document, assign the new operations, call each from the test agent

## Phase 3: Search, recovery and LLM-ready OpenAPI

Goal: `search_products` (filters only) working, every response within its budget and giving the agent what it needs to decide and recover, and OpenAPI descriptions good enough to steer tool choice (decision D7).

- [x] `GET /products/search`, declared before `/products/{product_id}`: price, recipient, occasion, `max_shipping_days`, `gift_wrap`, out-of-stock flag, sort, pagination; no filters returns the best-rated products
- [x] Deduplicate cross-listed products in search results (primary listing only)
- [x] Response budget tests: `limit=25` under 2.6k tokens (*Response budget* in the spec); done for browsing in Phase 2, add for search
- [x] Empty-result `suggestions` on both list tools (one relaxation at a time, at most 3, only ones that match)
- [x] `outside_price_range` on `search_products` (done for browsing in Phase 2: `above_max` / `below_min`, count and nearest price, over every other filter)
- [x] `applied_filters` echo (Phase 2, shared by both list tools)
- [x] Write the final operation, parameter and field descriptions (start from the spec drafts)
- [x] Test: every operation has `operationId`, `summary` and `description`; every parameter and response field has a description (`tests/test_openapi.py`, Phase 1; covers new operations automatically)
- [x] Tests for the spec acceptance criteria (search housewarming €40–60 = 13 products with no duplicate tumbler set; search `recipient=kids` returns only `KI-*`; `electronics` and Knives-under-€100 already covered in Phase 2)
- [x] Structured request logging with key fingerprint (brought forward, done 2026-10-29)
- [x] Redeploy (live, verified against the public `/openapi.json`, 2026-10-29)
- [x] Re-import the tool collection, check every operation in the test agent
- [x] Per-key rate limit (`429 rate_limited`) (brought forward, done 2026-10-29)

## Phase 4: The assistant

Goal: the gift assistant live on the platform, passing the NRT simulation suite (decision A1; evaluators and guardrails are not available in this workspace).

- [x] Write `agent/global-settings.md` (tone of voice, company description), `agent/gift-assistant.md` (trigger, Agent Block sections, settings; about 2.2k tokens) and `agent/general-agent.md` (the customised fallback), from the agent spec's *Architecture*
- [x] `agent/greeting.md`: the welcome message for the Greeting panel
- [x] Configure Global Agent Settings, the Gift Assistant (with the four tools, on `gpt-5.6-luna (EU)`, decision A2) and the General Agent (also on `gpt-5.6-luna (EU)`) on the platform; record every binding step in `agent/tools.md` so it can be reproduced
- [x] Format check on the shareable link at phone width: each recommendation fits one screen
- [x] Write `agent/simulations.csv` (19 simulations, E1–E13 and E15–E20, with suites)
- [x] Import `agent/simulations.csv` and set the suites (`agent/tools.md`, *Simulations*)
- [x] Security layer: edit the generated perimeter (gift shopping plus the shop's own questions), set it to Manual with automatic regeneration off, built-in jailbreak agent for jailbreaks and General Agent for out-of-scope, mode **Enforce**
- [x] Run the NRT suite; record the first run in `agent/evals.md`, including the tool-choice check from the service logs
- [x] Iterate: fix failures in the prompt or the tool descriptions (and in the spec first, if behaviour changes the contract)
- [x] Decision point for D7: check in the transcripts that the agent picks `search_products` for constraint-led requests and browsing for named product types (E1, E3, E8); if it keeps needing free-text lookup, consider D7's revisit path through the spec first
- [x] Check the runs for Security layer false positives: no shopping message blocked
- [x] Re-run the NRT suite until it passes; record the dated result
- [x] Publish the workspace (tool collection and agent) to Production; check a production tool call shows the `platform-prod` key fingerprint
- [x] Generate the public link and test it in a private window, logged out

## Phase 5: Hardening and handover

Goal: the client can open the link, read the repo, and follow every decision.

- [x] Final NRT run, recorded in `agent/evals.md` (runs 16–17: 19/19 and 18/19)
- [x] Droplet hygiene: unattended security upgrades on, Docker restart policy verified after a reboot, certificate renewal working (done by the developer, 2026-10-29)
- [x] Final check that the public spec URL, `/docs` and `/redoc` work from a logged-out browser, and that the platform's Production collection was imported from the current version
- [x] `README.md`: what it is, the API base URL, how to authenticate (link to `AUTHENTICATION.md`), how to run locally, where decisions are recorded (2026-10-29)
- [x] `README.md`: the live assistant link, once published
- [x] `README.md` agent sections (`AGENT_SPEC.md`, *README requirements*): the prompt, how the tools were bound, and the conversation design decisions, leading with how many questions are asked before recommending and why
- [x] `PLAYBOOK.md` and `docs/guides/testing.md` reflect the real commands (every command run on a clean copy, 2026-10-29; re-check if commands change)
- [x] Decision summary for the walkthrough: data cleaning, how the tools evolved (D5 → D6 → D7: why search was added back without free text), the response budget, error design, `outside_price_range`, recipient semantics, cross-listing, question rule, message format, what was left out (`WALKTHROUGH.md`)
- [x] Mark both specs **Implemented**; move this roadmap to `archive/`
