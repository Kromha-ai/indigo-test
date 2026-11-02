# Gift Shop Catalog Service and Gift Assistant

A product discovery assistant for an online gift shop. Shoppers describe who a gift is for and roughly what they want; the assistant asks at most one round of questions and recommends two or three products, each with a reason.

The shop's only data was a CSV export of its catalogue. This repository turns it into an authenticated API whose OpenAPI document is imported as tools by the assistant on the indigo.ai platform.

| | |
|---|---|
| Live assistant | [https://clair.platform.indigo.ai/chatbot/0f86001f-e9c2-4599-9748-739a04cb16f9](https://clair.platform.indigo.ai/chatbot/0f86001f-e9c2-4599-9748-739a04cb16f9) |
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

Every list response is compact and bounded: 10 summaries by default, at most 25, about 1k–2.5k tokens, with no descriptions. When the budget excludes something relevant, `outside_price_range` says so (for example *"1 more Knives product: the Chef's Knife 20cm at €149"*). When nothing matches, `suggestions` names the one constraint to relax. An unknown category or product ID returns `found: false` with `did_you_mean`, so the assistant can correct itself.

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
uv run pytest                             # 195 tests, no network or secrets needed
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
| `docs/planning/` | [The roadmap](docs/planning/ROADMAP.md): the optional site widget; the completed phases are in [`archive/`](archive/roadmap-phases-1-5.md) |
| `archive/` | Why things are the way they are, every decision with the options considered: [the API](archive/catalog-spec-decisions.md) and [the assistant](archive/agent-spec-decisions.md) |
| [`AUTHENTICATION.md`](AUTHENTICATION.md) | How callers authenticate, and why this scheme |
| [`WORKFLOW.md`](WORKFLOW.md) | How the project is run: spec first, then plan, then code |
| [`WALKTHROUGH.md`](WALKTHROUGH.md) | The decisions in one read: data cleaning, tool design, tuning the assistant, what was left out |

## The assistant

The assistant runs on indigo.ai as two agents. Their configuration is versioned in [`agent/`](agent/README.md), and the behaviour they implement is specified in [`AGENT_SPEC.md`](docs/specs/AGENT_SPEC.md).

### The prompt

**Two agents, split by routing.** Every message first passes the platform's Security layer, then goes to the agent whose trigger matches:

```
message ──▶ Security layer ── jailbreak attempt ──▶ built-in jailbreak agent
                  │         └── out of scope ──▶ General Agent
                  └── otherwise ──▶ Gift Assistant (trigger) or General Agent (fallback)
```

- **Gift Assistant**: the only agent with tools. Its trigger is deliberately broad: any message about a gift or a product, including follow-ups and short answers with no gift words in them ("for my dad", "about 30", "he's into football"). A shopping message that reaches the other agent meets an agent that cannot see the catalogue, so erring towards the Gift Assistant is the safe side.
- **General Agent**: greetings, small talk, off-topic questions and the shop's own questions (returns, delivery costs, orders), which it answers by pointing to customer service without inventing a policy. It never mentions a product, because it has no catalogue access.
- **Stateful Agents is off**, so every message is routed afresh. With it on, the agent that answered an aside ("what's the weather like?") kept the conversation and never handed it back.

**The Gift Assistant's Agent Block** ([`agent/gift-assistant.md`](agent/gift-assistant.md)) is short and imperative, about 1.2k words, because a model follows a few sharp rules better than many overlapping ones:

| Section | What it holds |
|---|---|
| Description, Goal | Who the assistant is and what a good outcome looks like: two or three in-stock recommendations, each with a reason, in as few turns as possible |
| General Rules | The ten hard rules, the first being the one that matters most: *"Only mention products, prices, ratings, shipping times or availability that a tool returned in this conversation."* |
| Questions before recommending | When to ask and when not to (below) |
| Reading the request | Shopper words to tool parameters: *"around 50 euros"* is `min_price=40, max_price=60`; *"just moved"* is the housewarming occasion, never a category; an interest is browsed where it lives (*"she loves singing"*: Tech & Gadgets, subcategory Audio) |
| Message format | The recommendation shape (below), preceded by one step: *"call get_product_details for each product you will show, and write the reason from its description"* |
| Hard cases | Specific requests, over budget, nothing suitable, out of stock, deadlines, gift cards, returning after an aside |
| Examples | Three: a recommendation in the target format, a vague request, an over-budget request |

Duplicate rules were removed, so each sits where the model acts on it. Tool choice lives in the tool descriptions, which are part of the API's code, so the prompt does not repeat it. The one exception is the details step: without it, the model wrote reasons and gift-wrap claims from data it had never fetched.

**Model**: the Gift Assistant runs on `gpt-5.6-luna (EU)` at Creativity 0.1 and reasoning Low; the General Agent on `gpt-4.1-mini (EU)`. On `gpt-4.1-mini` the Gift Assistant broke different rules from run to run, once inventing products, and no prompt change moved the results measurably; `gpt-5.6-luna` met the release bar and broke fewer rules, at a lower price tier than the *power* models ([decision A2](archive/agent-spec-decisions.md)).

### How the tools are bound to the agent

The Catalog Service becomes the agent's tools through its OpenAPI document. Every step is in [`agent/tools.md`](agent/tools.md); in short:

1. **Secret**: the workspace secret `CATALOG_API_KEY` holds a different key per environment, `platform-test` in Test and `platform-prod` in Production. The service logs a fingerprint of the key on every request, so it is easy to confirm which environment called.
2. **Tool collection** *Gift Shop Catalog*: created by importing a file of the OpenAPI document downloaded from [`/openapi.json`](https://catalog.builtbykromha.com/openapi.json). Endpoint `https://catalog.builtbykromha.com` for both environments, and the header `X-API-Key` set to the secret.
3. **Operations**: the import creates one action per `operationId`. All four are assigned to the Gift Assistant; the General Agent has none.
4. **Descriptions come from the code.** The operation and parameter descriptions are what the model reads to choose a tool and fill its parameters, so they are edited in the service and never in the platform form.
5. **After any API change**: deploy, download the document again, re-import it, then Publish and re-run the simulations. The platform does not refresh a collection on its own.

### Conversation design decisions

**How many questions before recommending: at most one round, and only when the request cannot be searched yet.** A request is searchable once it gives a product type (*"a chef's knife"*), an interest (*"she loves coffee"*), or who it is for plus an occasion or a budget. Then the assistant recommends straight away. For *"I need a gift"*, it asks once, in one message, for whatever is missing among who it is for, what they are into and the budget, with example answers. After that it recommends whatever the answer.

- **Each question costs a shopper.** A second round reads as a questionnaire, which is what the shop wants to avoid.
- **A recommendation is the best clarifying question.** Three varied options let the shopper react (*"more like the candle"*), which is easier than describing a person in the abstract, and the closing line narrows from there.
- **The greeting does part of the work.** It invites a free description (*"Tell me who the gift is for and anything you know about them…"*), so the first message is often already searchable.

**The recommendation message** fits one phone screen, about 90 words:

```
Three ideas for her new flat, all around €50:

**Reed Diffuser, Cedar · €46**: Makes a new place smell like home straight away, with no flame, and it ships in 2 days.

**Ceramic Planter, Medium · €52**: A first plant for the flat: it comes with its own saucer, and gift wrap is available.

**Linen Table Runner · €48**: Dresses up her new table for the first dinner she hosts there.

Something more personal, cheaper, or more like one of these?
```

- **Three products**: real choice without a scroll. Fewer when fewer genuinely fit; the shortlist is never padded with unrelated products.
- **One paragraph each**: name and price in bold, then on the same line a reason tied to what the shopper said plus one fact that helps them decide. Shipping time, gift wrap and low stock appear only when they matter; IDs, brands, tags and descriptions never do.
- **One closing line** offering directions for the same gift (cheaper, different, more like one of them), never a new question about someone else.
- **Bold only the name and price**: the name and price stand out when the shopper scans the reply; no headings, lists or tables.

**The hard cases:**

| Situation | Behaviour |
|---|---|
| Specific (*"a chef's knife under €100"*) | Browse the subcategory straight away. The only chef's knife is €149, so say so, and offer the €69 paring knife or the €54 sharpening stone. The API names the cheapest over-budget product, so the assistant can say this without a second call |
| Over budget after a recommendation (*"too expensive"*) | Keep every other constraint and show the closest options under the new limit |
| Nothing suitable (*"something for my cat"*) | Say so in one sentence, after trying the API's `suggestions`, and offer a gift card |
| Out of stock | Never recommended. If the shopper asks for it, say so and offer up to two in-stock alternatives |
| Deadline (*"by tomorrow"*) | Filter by shipping time; if nothing physical arrives in time, offer a gift card, delivered instantly by email. Never promise a delivery time a tool did not return |
| Off-topic, shop policies, attempts to change the instructions | The General Agent or the jailbreak agent: a short answer, nothing invented, back to gifts |

**Gift cards** (€50 and €100) are a fallback, never the first idea for a recipient the shopper has described: only when nothing fits, nothing arrives by the deadline, or the shopper knows very little about the recipient.

**How it is tested.** The behaviour is specified as scenarios and run as 19 platform simulations: an AI shopper plays each one, and a judge scores the transcript against its success criteria. The release bar is 18 of 19 or better in two consecutive runs, with no invented products. Because the judge does not see tool calls, tool choice is checked in the service logs. Every run, what failed and what was changed is in [`agent/evals.md`](agent/evals.md).
