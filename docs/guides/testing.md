# Testing Guide

**Last updated**: 2026-10-29

> Commands below are the target set by `docs/specs/CATALOG_SPEC.md`. They become real in roadmap Phase 1. Update this guide if they change.

---

## Catalog Service

### Running tests

```bash
cd catalog-service
uv run pytest            # everything
uv run pytest -k search  # by name
uv run pytest --cov=app --cov-report=term-missing
uv run ruff check . && uv run ruff format --check .
```

Tests need no network, no database and no secrets. The test settings inject a fixed API key.

### Where tests live

| Folder | What it covers |
|---|---|
| `tests/test_build.py` | The build step: normalisation, derived fields, cross-listings, report, determinism, and the staleness check on the committed `data/catalog.json` |
| `tests/test_loader.py` | Startup validation of `catalog.json` (a truncated or malformed file refuses to load) |
| `tests/test_auth.py` | Missing, wrong and valid keys; unauthenticated routes stay open |
| `tests/test_<tool>.py` | One file per tool, exercised through `TestClient` |
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
- **Response budget.** Tests request `limit=25` on both list tools and a product detail, and assert the serialised size stays under the budget in the spec's *Response budget* table (characters / 3.6 as the token estimate).
- **Bug fixes ship with a failing test first** (see `WORKFLOW.md`, Step 4).

## Gift Assistant

The agent is tested by scenario, not by unit test. `agent/evals.md` holds the scenarios (E1–E17 in `docs/specs/AGENT_SPEC.md`) with expected behaviour. Run them by hand in the platform's test chat after any prompt or tool-description change.

For each run, record:

- the date and what changed since the previous run;
- pass/fail per scenario, with a one-line note for each failure;
- for failures, whether the cause was the prompt, a tool description or the API, and where it was fixed.

A change to a tool description is also a Catalog Service change: redeploy, re-import the tool collection from the public `/openapi.json`, re-run the evals, then Publish.
