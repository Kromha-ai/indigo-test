# Platform setup

How the workspace is configured, step by step, so it can be rebuilt.

## 1. Secret

**Workspace settings → Secrets**

| Name | Test value | Production value |
|---|---|---|
| `CATALOG_API_KEY` | the `platform-test` key | the `platform-prod` key |

Keys are never written here (`docs/guides/secrets-management.md`).

## 2. Tool collection

**Agent settings → Integrations → Tool Collections → Create Custom Tool Collection**

| Field | Value |
|---|---|
| Name | `Gift Shop Catalog` |
| Operations | Imported from a file: the OpenAPI document downloaded from `https://catalog.builtbykromha.com/openapi.json` |
| Endpoint, Test | `https://catalog.builtbykromha.com` |
| Endpoint, Production | `https://catalog.builtbykromha.com` |
| Header | `X-API-Key` = `[[CATALOG_API_KEY]]`, inserted with **Add secret** (the reference is the whole value) |

Imported operations: `get_categories`, `get_products_by_category`, `search_products`, `get_product_details`. They are read-only in the form, which is expected. Names and descriptions are never edited here; they come from the service's code.

After any API change: deploy, download the document again (`curl -s https://catalog.builtbykromha.com/openapi.json -o openapi.json`) and re-import it by hand from the file. The platform does not refresh the collection on its own.

## Environments

Every edit goes to **Test** (the *Draft*), and **Preview** runs against it. **Production** (shown as *Live*) changes only on **Publish**, which ships the whole workspace at once. Editing an agent listed under Live is fine: the change lands in Test, and the agent then appears under Draft until the next Publish. Publish only when both agents and the Security layer are ready. Secret and variable values are set per environment.

## 3. Global Agent Settings and Security layer

From `global-settings.md`: tone of voice, company description, Security layer in **Enforce**, with the built-in jailbreak agent for jailbreak attempts and the General Agent for out-of-scope requests, and the edited perimeter (Manual, automatic regeneration off).

## 4. Agents

| Agent | Source | Tools | Model |
|---|---|---|---|
| Gift Assistant | `gift-assistant.md` | The 4 operations of *Gift Shop Catalog* | `gpt-5.6-luna (EU)`, reasoning Low |
| General Agent | `general-agent.md` | None | `gpt-4.1-mini (EU)` |

The greeting: `greeting.md`, pasted into the workspace's Greeting panel.

## 5. Quality

Evaluators and guardrails are not available in this workspace: the **Improve** menu has only Issues, Simulations and Playground. Quality rests on the agents' prompts and is checked by the simulations.

## 6. Simulations

Import `simulations.csv` in **Improve → Simulations → Import**. Its columns match the platform template (`name, prompt, success_criteria, good_output, bad_output, suite, max_messages`). Every field is a single line: the importer rejects quoted fields longer than 10 lines.

The CSV's `suite` column holds each simulation's main suite. After importing, add every simulation to the **No Regression Test (NRT)** suite, and add the ones below to their extra suites:

| Simulation | Suites |
|---|---|
| E1, E8, E15, E16, E17 | NRT, Tool choice |
| E3 | NRT, Hard cases, Tool choice |
| E5, E6, E7, E9 | NRT, Hard cases |
| E4 | NRT, Hard cases, Routing |
| E2, E18 | NRT, Routing |
| E19 | NRT, Routing, Tool choice |
| E20 | NRT, Routing |
| E10, E11 | NRT, Off-topic and safety, Routing |
| E12 | NRT, Off-topic and safety |
| E13 | NRT, Language |

## 7. Checks

- [x] A Test-environment tool call succeeds, and the service logs show the `platform-test` key's fingerprint (`docker compose -f deploy/docker-compose.yml logs --tail=20 catalog-service` on the droplet).
- [x] After Publish, a Production tool call shows the `platform-prod` fingerprint.

## Observed on the platform

Also summarised in `docs/specs/AGENT_SPEC.md` (*Observed on the platform*):

| Question | Answer |
|---|---|
| What the model sees when a tool returns 4xx | Not needed: every recoverable case returns `200` with `found: false`, `error.hint` and `did_you_mean` |
| Tool call timeout | Not measured: the service answers in under 10 ms (`latency_ms` in the access log) |
| Shareable link: how it is produced, access settings, which environment it serves | The chatbot's public link; opens logged out and serves **Production** (published version, `platform-prod` key) |
| Does the simulation judge see tool calls? | **No**: it judges the visible text only ("stock not confirmed", "not clear the alternatives are in the catalogue"). Tool choice is checked in the service logs |
| Which environment simulations run against | **Live (Production)**: an agent must be published before simulations can test it |
| Language of the judge's explanations | The workspace language (Italian) |
| Evaluators and guardrails | Not available in this workspace |
| Routing of follow-ups: routed afresh, or the active agent keeps the conversation? | With **Stateful Agents off**, every message is routed afresh by trigger. With it on, the agent that answered an aside kept the conversation (E18) |
