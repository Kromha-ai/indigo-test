# Catalog Service: decision record

**Archived**: 2026-10-29 · **Spec**: `docs/specs/CATALOG_SPEC.md`

The *why* behind the Catalog Service contract, moved out of the spec to keep it short. **The spec is the source of truth**: every accepted decision below is already reflected there. This file explains how it got that way, and backs up the walkthrough. Superseded decisions are kept for their reasoning. Do not treat them as current.

Authentication (D1) has its own record in `AUTHENTICATION.md`.

| # | Decision | Status |
|---|---|---|
| D1 | Authentication scheme | Accepted (`AUTHENTICATION.md`) |
| D2 | Recoverable errors return `200` + `found: false` | Accepted |
| D3 | One deployment for both platform environments | Accepted |
| D4 | Hosting on a DigitalOcean VPS | Accepted |
| D5 | Narrow keyword `query` with no dead end | Superseded by D6 |
| D6 | Browse-first with three tools, no search | Superseded by D7 |
| D7 | Four tools: filters-only search added, response budget | Accepted |

---

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

**Status**: Superseded by D7 · 2026-10-29 · supersedes D5

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

### D7: Four tools: filters-only search added, response budget

**Status**: Accepted · 2026-10-29 · supersedes D6

**Context**: two questions shape the tool design:

- **What comes back, in what shape, and how much of it?** The response size must stay within the agent's context window, even with a category of forty products with long descriptions.
- **Do three operations cover the conversations the assistant must support?** If not, what is missing, and why?

D6 answered both by relying on the catalogue being small: the page limit of 30 was sized to the largest category (28), and browsing was justified by the whole catalogue fitting in about 10k tokens. That reports a fact about today's export instead of solving the problem. And the flagship conversation (recipient + occasion + budget) has matches in five categories, so with three operations the agent has to guess and merge categories.

**Options**:

- **(A)** Keep D6.
- **(B)** Add `search_products` with filters only, no free text, and size every response by a token budget.
- **(C)** Bring back D5's keyword `query` as well.

**Decision**: (B).

- **Three operations are not enough** for constraint-led requests. One cross-category filter tool covers them in a single, deduplicated call.
- **No free text**: keyword matching failed when tested (D5). Moods and tastes stay with the agent, now judged over a short, relevant list instead of whole categories.
- **Every response has an explicit budget**:
  - lists default to 15 summaries and cap at 25;
  - summaries never carry descriptions;
  - descriptions are capped at 300 characters at build time;
  - `total` and `next_offset` signal more.

  The shape holds unchanged at 40 products per category or ten times the catalogue.

**Consequences**:

- **Back**: `search_products` (filters only), `search_too_broad`, `listing_group` / `is_primary_listing` for deduplication, `category` in summaries.
- **Kept from D6**: `tags` in summaries, `in_stock_by_occasion`, `outside_price_range` (on both list tools), the `max_shipping_days` and `gift_wrap` filters.
- **Not back**: `query`, `search_weights`, `near_misses`, `interests`.
- **Tool choice is carried by the descriptions**: `search_products` for gift requests defined by constraints, `get_products_by_category` when the shopper names a kind of product. The evals check that the agent picks correctly (E1, E3, E8).
- **Larger categories need two pages** (Home & Living: 26 in stock, limit 25). This is intended: the agent narrows with filters instead.

**Revisit if** the evals show the agent consistently needs free-text lookup that browsing by subcategory cannot give. The candidate then is D5's narrow `query`, added to `search_products` as an optional parameter (an additive change under D3).

---

## Rationale notes moved from the spec

### Why `search_products` exists, and why it has no free-text query

**Why it was added**: the conversation this assistant exists for (*"something for my sister, she just moved into a new flat, maybe fifty euros"*) is defined by recipient, occasion and budget, not by category. Its matches sit in five categories. With only the three original operations, the agent has to guess categories, fetch several and merge them in its head. That costs context, costs round trips, and misses the best product in a category it did not think of. One filtered call answers it, deduplicated.

**Why it has no free-text `query`**: keyword matching was tested on 60 shopper words and failed exactly where it mattered (*cosy*, *pamper*, *music*, *gaming* found nothing; descriptions caused false positives). See D5. The filters narrow the list, and the agent judges moods and tastes from the summaries.

### Why summaries carry `tags`

- `tags` are included because, with no free-text search, they are the agent's best matching signal after the name. Measured cost: +18% tokens (the largest category goes from ~1,950 to ~2,300).
- `shipping_days` is included because delivery time often decides between two candidates (*"it ships in two days"*).

### `rating_score` sanity check

- With the current data, the top of the ranking is the E-Reader (4.8 from 923 reviews), the Ember Candle (4.8 from 431) and the Chef's Knife (4.8 from 394), which matches intuition.

### `outside_price_range` and subcategories

This is how the agent learns that what the shopper asked for exists just over budget. *"A chef's knife under €100"* browsed as `subcategory=Knives, max_price=100` returns the paring knife and the sharpening stone, plus `above_max: {count: 1, min_price_eur: 149}`: the chef's knife. Without the subcategory, the same browse over all of Kitchen & Dining says *"5 more from €115"*, which is true but not useful, which is why specific product types are browsed by subcategory.

### Response budget at larger scale

**At larger scale** (a category with forty products and long descriptions, or a catalogue ten times bigger), nothing in the response shape changes:

- Lists still return at most 25 compact summaries, best first.
- Descriptions never enter lists, and are capped in details.
- The agent narrows with filters rather than paging: its instructions allow at most two pages of any list (*AGENT_SPEC.md*, hard rules).
- `total` tells it, and the shopper, how much more there is.

### Description cap

**Removed 2026-10-29.** Descriptions are kept whole at build time. If long copy ever becomes a problem, it will be handled with something better than truncation.

| `description` | Trim. Capped at 300 characters, cut at the last sentence boundary before the cap; every cut is listed in `BUILD_REPORT.md` | Currently at most 142 characters, so nothing is cut. The cap is what keeps detail responses bounded if a future export has long copy |

### 4xx visibility: the accepted cost of D2

**Accepted cost**: if the platform hides 4xx bodies, the model gets a generic failure for `invalid_parameter` and `search_too_broad`. These are agent mistakes, not shopper situations; tool descriptions, enums and evals are what prevent them. The Phase 1 spike still records what the platform does with 4xx, for the README.
