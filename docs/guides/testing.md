# Testing Guide

**Last updated**: 2026-10-29

> Update this guide if a command changes.

---

## Catalog Service

### Running tests

```bash
cd catalog-service
uv run pytest            # everything
uv run pytest -k auth    # by name
uv run ruff check . && uv run ruff format --check .
```

Tests need no network, no database and no secrets. The test settings inject a fixed API key.

### Where tests live

| Folder | What it covers |
|---|---|
| `tests/test_build.py` | The build step: normalisation, derived fields, cross-listings, report, determinism, and the staleness check on the committed `data/catalog.json` |
| `tests/test_loader.py` | Startup validation of `catalog.json` (a truncated or malformed file refuses to load) |
| `tests/test_auth.py` | Missing, wrong and valid keys; unauthenticated routes stay open |
| `tests/test_categories.py`, `test_browse.py`, `test_search.py`, `test_products.py` | Each tool through `TestClient` against the real catalogue, plus `/health` |
| `tests/test_suggestions.py` | Empty results: which relaxations are offered, their counts, order and cap |
| `tests/test_rate_limit.py`, `test_logging.py` | Per-key limit with a fake clock; one JSON log line per request, key never logged |
| `tests/test_errors.py` | Every error code in the spec and its recovery content |
| `tests/test_openapi.py` | Contract of the OpenAPI document (below) |
| `tests/fixtures/*.csv` | Tiny hand-written CSVs for edge cases (bad price, unknown category, empty fields) |

### Conventions

- **Test at the HTTP boundary.** The platform calls HTTP, so the tests do too. Go through `TestClient` with the `X-API-Key` header, not through internal functions. Build and loader tests are the exception.
- **The real data is a fixture.** Acceptance criteria in the spec are written against the committed export and its build (11 categories, 13 housewarming products at €40–60, and so on), so assert those numbers directly. If the client sends a new export, these tests are supposed to fail: rebuild, re-profile (`docs/reference/catalog-data-profile.md`) and update.
- **The build is under contract.** `test_build.py` runs the build in memory and compares it with the committed `data/catalog.json`. A mismatch means someone changed a mapping or the script without regenerating, or hand-edited the data.
- **Edge cases use small fixture CSVs** fed to the build (bad price, unknown category, unknown recipient), so each test shows its own input.
- **Assert the shape the agent reads**: `found`, `error.code`, `hint` and `did_you_mean`, not only the status code. Recoverable cases are `200` (decision D2), so a status-only assertion would pass on a broken response.
- **The OpenAPI document is under contract.** `test_openapi.py` fails if any operation lacks `operationId`, `summary` or `description`, or if any parameter or response field lacks a description. Tool descriptions drive the agent, so a missing one is a bug.
- **Response budget.** Tests request `limit=25` on both list tools and assert the serialised size stays under the budget in the spec's *Response budget* table (characters / 3.6 as the token estimate).
- **Bug fixes ship with a failing test first** (see `WORKFLOW.md`, Step 4).

## Gift Assistant

The assistant is tested by scenario, on the indigo.ai platform (`docs/specs/AGENT_SPEC.md`, *Evaluation*).

### Running the simulations

After any change to the prompt, a tool description or the API:

1. Edit `agent/simulations.csv` if a scenario changed, then import it in **Improve → Simulations** (replacing the previous version).
2. Run the **NRT** suite, or a smaller suite while iterating (*Tool choice*, *Hard cases*, *Off-topic and safety*, *Routing*).
3. For the tool-choice scenarios (E1, E3, E8, E15–E17, E19), check which tools were called in the Catalog Service's logs on the droplet:

   ```bash
   docker compose -f deploy/docker-compose.yml logs --since 30m catalog-service | grep catalog.access
   ```

   Each line shows `operation` (e.g. `search_products`) and `query` (the filters used).
4. Re-run a failing simulation once and read its transcript before changing the prompt: the role-player and the judge are both LLMs.
5. Check that no shopping message was blocked by the Security layer: a shopping simulation answered by the jailbreak agent or the General Agent is a false positive. Record it in the run's entry; the fix is in the perimeter.

### Recording a run

Each run gets a dated entry in `agent/evals.md`:

- what changed since the previous run;
- the suite and its result (passed / total);
- for each failure: the platform's explanation, whether it reproduced on re-run, the cause (prompt, tool description or API) and where it was fixed;
- the tool-choice check from the logs.

A change to a tool description is also a Catalog Service change: redeploy, download the OpenAPI document and re-import the tool collection from the file, run the NRT suite, then Publish.

### Live monitoring

Evaluators and guardrails are not available in this workspace, so real conversations are reviewed in **Observe → Conversation Logs**. A conversation that went wrong becomes a new simulation (**From a real conversation**), so the fix is tested from then on.
