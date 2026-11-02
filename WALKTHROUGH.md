# Walkthrough

The decisions behind the gift assistant, in the order they were made. Each section is a summary; the full reasoning, with the options considered, is in [`archive/catalog-spec-decisions.md`](archive/catalog-spec-decisions.md) (the API) and [`archive/agent-spec-decisions.md`](archive/agent-spec-decisions.md) (the assistant).

## 1. Cleaning the data

The client's CSV export is never edited. A build step (`catalog-service/catalog_build/`) turns it into `catalog.json`, the only file the service reads, and writes `BUILD_REPORT.md` beside it listing every fix.

| What the export had | What the build does |
|---|---|
| 17 spellings of 11 categories (`home & living`, `Home and Living`, a leading space…) | Maps each to one canonical category with a URL slug (`home-living`) |
| Two products listed twice under different IDs and categories | Keeps both listings, marks the lower ID as primary, and links them with `also_listed_in`, so the assistant never recommends the same product twice |
| 11 products with no stock, and `999` on the gift cards as "unlimited" | Exposes `availability` (`in_stock`, `low_stock` for 1–5 units, `out_of_stock`), never raw counts. Out-of-stock products are hidden from lists by default |
| Products with no reviews | `rating: null`, never `0` |
| Ratings from a dozen reviews next to ratings from hundreds | A rating weighted by review count, used only for ranking, so 4.8 from 12 reviews does not outrank 4.7 from 400 |

A row that cannot be normalised fails the build, and an invalid `catalog.json` stops the service from starting. The committed file must match a fresh build.

## 2. Shaping the tools

The tools went through three designs before the current one:

1. **Keyword search (D5).** Tested against 60 typical shopper words, it failed on exactly the words that matter: *cosy*, *pamper*, *music* and *gaming* found nothing, and descriptions produced false positives (`cat` matched a diffuser).
2. **Browse only (D6).** Three tools, with the model reading whole categories and judging taste itself. It worked only because the catalogue is small, and the main conversation (*"my sister, new flat, about €50"*) has matches in five categories, so the agent had to guess and merge.
3. **Four tools with a response budget (D7, current).** `search_products` came back with filters only (recipient, occasion, budget, deadline, gift wrap), no free text, for requests defined by constraints. Browsing stays for named product types and interests. `get_product_details` gives the description for the reason; `get_categories` answers "what do you sell?".

Design choices that cut across the tools:

- **A response budget.** Lists return 10 summaries by default and 25 at most, about 1k–2.5k tokens, with no descriptions. The shape holds at ten times the catalogue: the agent narrows with filters instead of paging.
- **Errors the agent can act on.** An unknown category or product returns `200` with `found: false`, a `hint` and `did_you_mean` (the closest valid categories or IDs), so the model corrects itself instead of seeing a generic failure (D2).
- **`outside_price_range`.** When a budget hides what the shopper asked for, the response says so and names the nearest product: *"a chef's knife under €100"* returns the paring knife and the sharpening stone, plus "1 more: the Chef's Knife 20cm at €149". Naming the product was added after the simulations showed the assistant could not tell the shopper which product the €149 was.
- **Recipient semantics.** `anyone` is a wildcard for adults only: `recipient=kids` never matches `anyone` products, because that bucket includes knives.
- **Descriptions are part of the contract.** The model chooses tools from their descriptions, so they are written and edited in code, and every change goes through deploy, re-import and the simulations.

## 3. Tuning the assistant

**Architecture.** Two agents: the Gift Assistant with the four tools, and the General Agent, with no tools, for greetings, off-topic questions and the shop's own questions. The platform's Security layer sends jailbreak attempts to its built-in jailbreak agent before either agent sees them.

**The question rule.** At most one round of questions, and only when the request cannot be searched yet. A request with a product type, an interest, or a recipient plus an occasion or budget gets recommendations straight away. Each question costs a shopper, and three varied options are a better clarifying question than a second round.

**The message format.** Three products, two lines each (name and price, then a reason tied to what the shopper said), a one-line lead-in and one closing line with directions: about 90 words, one phone screen. Plain text, because the platform's chat does not render bold.

**What the simulations changed.** The behaviour is specified as scenarios and run as 19 platform simulations. Fifteen runs shaped the result:

- **Routing.** Short answers (*"for my dad"*, *"about 30"*) reached the agent with no tools. The trigger was broadened to cover them, and Stateful Agents turned off, because with it on the General Agent kept the conversation after an aside and described a candle it had never looked up.
- **Tool choice, read from the service logs** (the judge does not see tool calls). The agent used occasions as categories, never set a subcategory and capped every list at three, so its shortlists were padded with unrelated products. The prompt now maps shopper words to parameters, and interests are browsed where they live.
- **Grounding.** The agent never called `get_product_details`, and once recommended products that do not exist. The prompt now requires the details call before every recommendation and the name and price copied from the tool.
- **The model.** On `gpt-4.1-mini` the failures moved from run to run: 12 to 17 out of 19 with the same prompt. A shorter prompt and lower creativity did not change that. `gpt-5.6-luna`, at a lower price tier than the *power* models, passed 18 of 19 in consecutive runs (A2). Later runs scored 15 to 17. With its reasoning effort set from None to Low, the scores barely moved, but the remaining failures became repeatable, and the logs showed why the most frequent one (E4) kept failing: browsing coffee with `occasion=birthday` hid the moka pot, which the client's export tags only for housewarming and thank-you. Interests are now browsed without occasion, and the last two runs scored 18 of 19 each.

**Release bar**: 18 of 19 or better in two consecutive runs, with no invented products. Every run is in [`agent/evals.md`](agent/evals.md).

## 4. What was left out, and why

| Left out | Why |
|---|---|
| Free-text and semantic search | Keyword matching failed on moods and interests; semantic search always returns *something*, which looks like relevance when it is not. The model judges taste better from a short filtered list |
| Orders, returns, delivery costs | The catalogue has no data on them. The assistant points to customer service and never invents a policy |
| A database | 150 products fit in memory; a new export means rebuild, review, redeploy |
| Personal data | Nothing about the shopper is needed or stored |
| Evaluators and guardrails | Not available in this workspace. Quality rests on the prompts and the simulations |
| Product cards and quick replies | The platform's chat shows plain text; cards belong to a web-widget phase, not to the shareable link |
| A stronger *power* model | It would raise the cost of every conversation. The current model has met the release bar; it is the next step if the remaining variance matters more than cost |
