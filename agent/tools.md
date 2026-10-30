# Platform setup

How the workspace is configured, step by step, so it can be rebuilt. Fill in the blanks (*to record*) while configuring.

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
| Gift Assistant | `gift-assistant.md` | The 4 operations of *Gift Shop Catalog* | `gpt-4.1-mini (EU)` |
| General Agent | `general-agent.md` | None | `gpt-4.1-mini (EU)` |

The greeting: `greeting.md`, pasted into the workspace's Greeting panel.

## 5. Quality

Evaluators and guardrails are not available in this workspace: the **Improve** menu has only Issues, Simulations and Playground. Quality rests on the agents' prompts and is checked by the simulations.

## 6. Simulations

Import `simulations.csv` in **Improve → Simulations → Import**. Before the first import, use **Download template** to confirm the column names.

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
- [ ] After Publish, a Production tool call shows the `platform-prod` fingerprint.

## Observed on the platform

Record answers here and in `docs/specs/AGENT_SPEC.md` (*Still to verify*):

| Question | Answer |
|---|---|
| What the model sees when a tool returns 4xx | *to record* |
| Tool call timeout | *to record* |
| Does a secret change need a Publish? | *to record* |
| Shareable link: how it is produced, access settings, which environment it serves | *to record* |
| Does the simulation judge see tool calls? | *to record* |
| Evaluators and guardrails | Not available in this workspace |
| Routing of follow-ups: routed afresh, or the active agent keeps the conversation? | *to record* |
