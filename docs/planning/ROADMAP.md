# Roadmap: Catalog Service and Gift Assistant

**Started**: 2026-10-29
**Specs**: `docs/specs/CATALOG_SPEC.md` · `docs/specs/AGENT_SPEC.md`

Five phases, each a shippable slice, plus an optional sixth. Every phase ends with the service deployable and tests green.

The order is deliberate. Phase 1 puts a thin service on the real platform first, so that whatever the platform does differently from what the docs suggest is found before the full API is built.

---

## Status

| Phase | Goal | Status |
|---|---|---|
| 1 | Walking skeleton on the platform | In progress: service live at catalog.builtbykromha.com (2026-10-29); platform tasks next |
| 2 | Browse and detail tools | Built and tested 2026-10-29; redeploy and re-import pending |
| 3 | Search, recovery, and LLM-ready OpenAPI | Built and tested 2026-10-29; redeploy and re-import pending |
| 4 | The assistant | Not started |
| 5 | Hardening and handover | Not started |
| 6 (bonus) | Site widget | Not started |

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
- [x] `GET /categories` (with subcategories, price ranges, `in_stock_by_occasion`) and `GET /health`
- [x] `servers` populated from `PUBLIC_BASE_URL`
- [x] OpenAPI spec published: `/openapi.json`, `/docs`, `/redoc` left at FastAPI defaults; auth applied as a router dependency so they stay public; tests that all three answer `200` without a key and that `/openapi.json` declares no header parameters
- [x] Dockerfile (ships `data/catalog.json`), `.env.example`
- [x] `deploy/`: `docker-compose.yml` (service only, bound to `127.0.0.1`, one worker, `--proxy-headers`, `restart: unless-stopped`), `catalog.caddy` (site block imported by the droplet's system Caddy), `.env.example`
- [x] Droplet: DNS A record for `catalog.builtbykromha.com` (check it resolves first), Docker, clone to `/var/www/indigo-test`, `deploy/.env`, `docker compose up`, `import` the site block in `/etc/caddy/Caddyfile` and reload Caddy; smoke-test `https://catalog.builtbykromha.com/health`
- [x] Check the public spec URL on the deployed host (`PLAYBOOK.md`, *Deploying*, step 4) and add it to `README.md` and `AUTHENTICATION.md`
- [ ] Read the rest of the platform guide (*Getting Started*, *Build Your AI Agents*) in a signed-in browser; note the platform's vocabulary
- [x] Generate the three keys (`platform-test`, `platform-prod`, `local-dev`) and set `CATALOG_API_KEYS` in `deploy/.env` on the droplet
- [ ] Set the `CATALOG_API_KEY` workspace secret on indigo.ai (Test and Production values) per `docs/guides/secrets-management.md`
- [ ] Create the agent from zero in the sandbox workspace
- [ ] Create the tool collection by importing from the public `/openapi.json` (`AGENT_SPEC.md`, *Tool binding procedure*), assign it to the agent, configure the API key, and call `get_categories` from a test agent
- [ ] Spike: check what the model sees on a 4xx (for the README; not blocking, see decision D2)
- [ ] Spike: the tool-call timeout (measure with a deliberately slow test endpoint if undocumented; for the README, since the VPS has no cold starts), whether a secret change needs a Publish, and how the public link works (which environment it serves)
- [ ] Record the spike answers in `AGENT_SPEC.md` (*Still to verify in Phase 1*), and in `AUTHENTICATION.md` / the secrets guide if a secret change needs a Publish
- [x] Mark `CATALOG_SPEC.md` **Approved**

## Phase 2: Browse and detail tools

Goal: `get_products_by_category` and `get_product_details` complete, with the full error envelope.

Prerequisite: Phase 1.

- [x] `ProductSummary` (with `tags`, `shipping_days`, `also_listed_in` on cross-listed products) and `ProductDetail` response models with field descriptions
- [x] Category resolution: slug, display name, case and whitespace insensitive, `and`/`&`
- [x] `GET /categories/{category}/products`: subcategory, price, recipient, occasion, `max_shipping_days`, `gift_wrap`, out-of-stock flag, `sort=best_rated` by `rating_score`, pagination (`limit` default 15, max 25), `ListResponse`
- [x] Recipient semantics: `her`/`him`/`couple` include `anyone`; `kids` exact
- [x] `GET /products/{product_id}`: case-insensitive ID, `also_listed_in`
- [x] Error envelope plus exception handlers; replace the default 422 body with plain-language `invalid_parameter` (built in Phase 1)
- [x] Tests for `invalid_parameter` once routes take parameters (e.g. `max_price` < `min_price`, `limit=0`)
- [x] `category_not_found` with fuzzy match and a synonym table; `subcategory_not_found`; `product_not_found` with near-ID suggestions, all as `200` + `found: false` (D2); `found: true` on success
- [x] HTTP-boundary tests for each tool, each error code, pagination edges (`offset` past the end, `limit` 1 and 25)
- [ ] Redeploy, re-import the tool collection from the public `/openapi.json`, assign the new operations, call each from the test agent

## Phase 3: Search, recovery and LLM-ready OpenAPI

Goal: `search_products` (filters only) working, every response within its budget and giving the agent what it needs to decide and recover, and OpenAPI descriptions good enough to steer tool choice (decision D7).

- [x] `GET /products/search`, declared before `/products/{product_id}`: category, price, recipient, occasion, `max_shipping_days`, `gift_wrap`, out-of-stock flag, sort, pagination; no filters returns the best-rated products
- [x] Deduplicate cross-listed products in search results (primary listing only)
- [x] Response budget tests: `limit=25` under 2.6k tokens (*Response budget* in the spec); done for browsing in Phase 2, add for search
- [x] Empty-result `suggestions` on both list tools (one relaxation at a time, at most 3, only ones that match)
- [x] `outside_price_range` on `search_products` (done for browsing in Phase 2: `above_max` / `below_min`, count and nearest price, over every other filter)
- [x] `applied_filters` echo (Phase 2, shared by both list tools)
- [x] Write the final operation, parameter and field descriptions (start from the spec drafts)
- [x] Test: every operation has `operationId`, `summary` and `description`; every parameter and response field has a description (`tests/test_openapi.py`, Phase 1; covers new operations automatically)
- [x] Tests for the spec acceptance criteria (search housewarming €40–60 = 13 products with no duplicate tumbler set; search `recipient=kids` returns only `KI-*`; `electronics` and Knives-under-€100 already covered in Phase 2)
- [x] Structured request logging with key fingerprint (brought forward, done 2026-10-29)
- [ ] Redeploy, re-import the tool collection, check every operation in the test agent
- [x] Per-key rate limit (`429 rate_limited`) (brought forward, done 2026-10-29)

## Phase 4: The assistant

Goal: the gift assistant live on the platform, passing the evaluation scenarios.

- [ ] Write `agent/system-prompt.md` from the agent spec (persona, question rule, flow, parameter mapping, message format, hard-case handling, hard rules, gift card policy)
- [ ] `agent/greeting.md` with 2–3 suggested starters
- [ ] Configure the agent on the platform with the four tools; record every binding step in `agent/tools.md` so it can be reproduced
- [ ] Format check on the shareable link at phone width: each recommendation fits one screen
- [ ] Write `agent/evals.md` (E1–E17) and run the first pass
- [ ] Iterate: fix failures in the prompt or the tool descriptions (and in the spec first, if behaviour changes the contract)
- [ ] Decision point for D7: check in the transcripts that the agent picks `search_products` for constraint-led requests and browsing for named product types (E1, E3, E8); if it keeps needing free-text lookup, consider D7's revisit path through the spec first
- [ ] Re-run E1–E17 and record the dated results
- [ ] Publish the workspace (tool collection and agent) to Production; check a production tool call shows the `platform-prod` key fingerprint
- [ ] Generate the public link and test it in a private window, logged out

## Phase 5: Hardening and handover

Goal: the client can open the link, read the repo, and follow every decision.

- [ ] Final full eval run, recorded in `agent/evals.md`
- [ ] Droplet hygiene: unattended security upgrades on, Docker restart policy verified after a reboot, certificate renewal working
- [ ] Final check that the public spec URL, `/docs` and `/redoc` work from a logged-out browser, and that the platform's Production collection was imported from the current version
- [ ] `README.md`: what it is, the live link, the API base URL, how to authenticate (link to `AUTHENTICATION.md`), how to run locally, where decisions are recorded
- [ ] `README.md` agent sections (`AGENT_SPEC.md`, *README requirements*): the prompt, how the tools were bound, and the conversation design decisions, leading with how many questions are asked before recommending and why
- [ ] `PLAYBOOK.md` and `docs/guides/testing.md` reflect the real commands
- [ ] Decision summary for the walkthrough: data cleaning, how the tools evolved (D5 → D6 → D7: why search was added back without free text), the response budget, error design, `outside_price_range`, recipient semantics, cross-listing, question rule, message format, what was left out
- [ ] Mark both specs **Implemented**; move this roadmap to `archive/`

## Phase 6 (bonus): Site widget

Goal: the assistant embedded in a web widget, as it would sit on the client's site, with formatting tuned for it.

Prerequisite: Phase 5. Not needed for the handover; the shareable link is the deliverable.

- [ ] Read *Configure & Install the Web Chat*: whether it adds quick-reply buttons, cards or carousels on top of Markdown, and its settings. It is embedded with `<script defer src="https://platform.indigo.ai/widget.js?token=<TOKEN>&v=3"></script>`; leave `uid` unset (anonymous shoppers)
- [ ] Decide the widget message format: quick replies for the next-step line, and cards only if they stay within one phone screen. Update `AGENT_SPEC.md` first
- [ ] Embed the widget in a minimal demo page and test it at phone width
- [ ] Re-run E1–E17 in the widget; record the results
- [ ] README: link to the demo page
