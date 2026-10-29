# Roadmap: Catalog Service and Gift Assistant

**Started**: 2026-10-29
**Specs**: `docs/specs/CATALOG_SPEC.md` · `docs/specs/AGENT_SPEC.md`

Five phases, each a shippable slice, plus an optional sixth. Every phase ends with the service deployable and tests green.

The order is deliberate. Phase 1 puts a thin service on the real platform first, because the platform unknowns (error visibility, OpenAPI version, auth configuration) change the API design. Finding them after the API is built would mean reworking it.

---

## Status

| Phase | Goal | Status |
|---|---|---|
| 1 | Walking skeleton on the platform | Not started |
| 2 | Browse and detail tools | Not started |
| 3 | Search, recovery, and LLM-ready OpenAPI | Not started |
| 4 | The assistant | Not started |
| 5 | Hardening and handover | Not started |
| 6 (bonus) | Site widget | Not started |

---

## Phase 1: Walking skeleton on the platform

Goal: a deployed, authenticated service with `get_categories` bound as a tool on the indigo.ai platform, and the remaining platform unknowns answered.

- [ ] Scaffold `catalog-service/`: `pyproject.toml` (uv), FastAPI app factory, settings from env, `ruff`, `pytest`
- [ ] Build step `catalog_build/build_catalog.py`: every normalisation rule, derived fields (`availability`, `rating_score`, `recipients_match`, `interests`, `listing_group`, `search_weights`), and fail-fast on bad rows
- [ ] `catalog_build/interests.toml` (from the spec's draft mapping, checked against the full tag list) and `catalog_build/synonyms.toml`
- [ ] Generate and commit `data/catalog.json`, `data/catalog.normalized.csv` and `data/BUILD_REPORT.md`; review the report
- [ ] Build tests against the real CSV: 152 records, 11 categories, the 6 drifted rows land in the right category, the 2 cross-listed pairs share a `listing_group`, 5 unrated products stay `null`, `kids` never in an `anyone` product's `recipients_match`, every subcategory but Gift Cards has an interest
- [ ] Build tests against small fixture CSVs: unknown category, bad price and unmapped subcategory abort the build; two runs give byte-identical output; committed `catalog.json` is not stale
- [ ] `app/loader.py`: load and validate `catalog.json` at startup, refuse to start on a malformed file
- [x] Sign off the authentication decision in `AUTHENTICATION.md` (Accepted 2026-10-29)
- [ ] `X-API-Key` auth dependency with multiple keys; refuse to start without keys; tests for missing, wrong and valid key
- [ ] `GET /categories` and `GET /health`
- [ ] `servers` populated from `PUBLIC_BASE_URL`
- [ ] OpenAPI spec published: `/openapi.json`, `/docs`, `/redoc` left at FastAPI defaults; auth applied as a router dependency so they stay public; tests that all three answer `200` without a key and that `/openapi.json` declares no header parameters
- [ ] Dockerfile (ships `data/catalog.json`), `.env.example`
- [ ] `deploy/`: `docker-compose.yml` (service bound to `127.0.0.1`, one worker, `--proxy-headers`, `restart: unless-stopped`; Caddy), `Caddyfile` (`catalog.builtbykromha.com`), `.env.example`
- [ ] Droplet: DNS A record for `catalog.builtbykromha.com` (check it resolves first), firewall (22/80/443), Docker; first deploy per `PLAYBOOK.md`; smoke-test `https://catalog.builtbykromha.com/health`
- [ ] Check the public spec URL on the deployed host (`PLAYBOOK.md`, *Deploying*, step 4) and add it to `README.md` and `AUTHENTICATION.md`
- [ ] Read the rest of the platform guide (*Getting Started*, *Build Your AI Agents*) in a signed-in browser; note the platform's vocabulary
- [ ] Generate the three keys; set `CATALOG_API_KEYS` in `deploy/.env` on the droplet and the `CATALOG_API_KEY` workspace secret (Test and Production values) per `docs/guides/secrets-management.md`
- [ ] Create the agent from zero in the sandbox workspace
- [ ] Create the tool collection by importing from the public `/openapi.json` (`AGENT_SPEC.md`, *Tool binding procedure*), assign it to the agent, configure the API key, and call `get_categories` from a test agent
- [ ] Spike: check what the model sees on a 4xx (for the README; not blocking, see decision D2)
- [ ] Spike: the tool-call timeout (measure with a deliberately slow test endpoint if undocumented; for the README, since the VPS has no cold starts), whether a secret change needs a Publish, and how the public link works (which environment it serves)
- [ ] Record the spike answers in `AGENT_SPEC.md` (*Still to verify in Phase 1*), and in `AUTHENTICATION.md` / the secrets guide if a secret change needs a Publish
- [ ] Mark `CATALOG_SPEC.md` **Approved**

## Phase 2: Browse and detail tools

Goal: `get_products_by_category` and `get_product_details` complete, with the full error envelope.

Prerequisite: Phase 1.

- [ ] `ProductSummary` and `ProductDetail` response models with field descriptions
- [ ] Category resolution: slug, display name, case and whitespace insensitive, `and`/`&`
- [ ] `GET /categories/{category}/products`: subcategory, price, recipient, occasion, out-of-stock flag, sort, pagination, `ListResponse`
- [ ] Recipient semantics: `her`/`him`/`couple` include `anyone`; `kids` exact
- [ ] `GET /products/{product_id}`: case-insensitive ID, `also_listed_in`
- [ ] Error envelope plus exception handlers; replace the default 422 body with plain-language `invalid_parameter`
- [ ] `category_not_found` with fuzzy match and a synonym table; `subcategory_not_found`; `product_not_found` with near-ID suggestions, all as `200` + `found: false` (D2); `found: true` on success
- [ ] HTTP-boundary tests for each tool, each error code, pagination edges (`offset` past the end, `limit` 1 and 25), and the size bound
- [ ] Redeploy, re-import the tool collection from the public `/openapi.json`, assign the new operations, call each from the test agent

## Phase 3: Search, recovery, and LLM-ready OpenAPI

Goal: `search_products` working with relaxation suggestions, and an OpenAPI document whose descriptions are good enough to drive the agent.

- [ ] `GET /products/search`, declared before `/products/{product_id}`, with every filter including `max_shipping_days` and `gift_wrap`
- [ ] Relevance scoring over `search_weights` with query-side synonym expansion; tie-break on `rating_score`; `search_too_broad`
- [ ] `interest` filter on both list tools; `sort=best_rated`
- [ ] Deduplicate cross-listed products in search results
- [ ] Empty-result `suggestions` for both list tools (one relaxation at a time, at most 3, only ones that match)
- [ ] `near_misses` on `search_products` (strong matches excluded only by price, at most 2)
- [ ] `applied_filters` echo
- [ ] Write the final operation, parameter and field descriptions (start from the spec drafts)
- [ ] Test: every operation has `operationId`, `summary` and `description`; every parameter and response field has a description
- [ ] Tests for the spec acceptance criteria (housewarming €40–60 = 13 products, kids returns only `KI-*`, `electronics` suggests `tech-gadgets`, chef's knife under €100 returns `KD-001` in `near_misses`)
- [ ] Structured request logging with key fingerprint
- [ ] Redeploy, re-import the tool collection, check every operation in the test agent
- [ ] Per-key rate limit (`429 rate_limited`)

## Phase 4: The assistant

Goal: the gift assistant live on the platform, passing the evaluation scenarios.

- [ ] Write `agent/system-prompt.md` from the agent spec (persona, question rule, flow, parameter mapping, message format, hard-case handling, hard rules, gift card policy)
- [ ] `agent/greeting.md` with 2–3 suggested starters
- [ ] Configure the agent on the platform with the four tools; record every binding step in `agent/tools.md` so it can be reproduced
- [ ] Format check on the shareable link at phone width: each recommendation fits one screen
- [ ] Write `agent/evals.md` (E1–E14) and run the first pass
- [ ] Iterate: fix failures in the prompt or the tool descriptions (and in the spec first, if behaviour changes the contract)
- [ ] Re-run E1–E14 and record the dated results
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
- [ ] Decision summary for the walkthrough: data cleaning, why `search_products`, response size bound, error design, `near_misses`, recipient semantics, cross-listing, question rule, message format, what was left out
- [ ] Mark both specs **Implemented**; move this roadmap to `archive/`

## Phase 6 (bonus): Site widget

Goal: the assistant embedded in a web widget, as it would sit on the client's site, with formatting tuned for it.

Prerequisite: Phase 5. Not needed for the handover; the shareable link is the deliverable.

- [ ] Read *Configure & Install the Web Chat*: whether it adds quick-reply buttons, cards or carousels on top of Markdown, and its settings. It is embedded with `<script defer src="https://platform.indigo.ai/widget.js?token=<TOKEN>&v=3"></script>`; leave `uid` unset (anonymous shoppers)
- [ ] Decide the widget message format: quick replies for the next-step line, and cards only if they stay within one phone screen. Update `AGENT_SPEC.md` first
- [ ] Embed the widget in a minimal demo page and test it at phone width
- [ ] Re-run E1–E14 in the widget; record the results
- [ ] README: link to the demo page
