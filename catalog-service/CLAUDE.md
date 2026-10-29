# catalog-service

FastAPI service exposing the gift shop catalogue as agent tools. The contract is `../docs/specs/CATALOG_SPEC.md`. Read it before changing any route, parameter, response field or description.

## Stack

Python 3.12 · FastAPI · Pydantic v2 · Uvicorn · uv · pytest · ruff

## Commands

```bash
uv sync                                    # install
cp .env.example .env                       # then set CATALOG_API_KEYS
uv run python -m catalog_build.build_catalog       # regenerate data/ from ../raw_data/ after any export or mapping change
uv run uvicorn app.main:create_app --factory --env-file .env --reload   # http://localhost:8000/docs
uv run pytest                              # tests
uv run ruff check . && uv run ruff format .
docker build -t catalog-service .           # the image ships data/catalog.json, not the raw CSV
# deployment (DigitalOcean droplet, behind its system Caddy): ../deploy/, see ../PLAYBOOK.md
```

## Layout

```
catalog_build/
  build_catalog.py   raw CSV → data/ (normalise, derive, report)
  synonyms.toml      category synonyms for did_you_mean
data/              build outputs, committed: catalog.json, catalog.normalized.csv, BUILD_REPORT.md
app/
  main.py        app factory (`create_app`): settings, catalogue, handlers, routers
  settings.py    env-driven settings
  auth.py        X-API-Key dependency
  loader.py      reads and validates data/catalog.json (record model, no FastAPI imports)
  catalog.py     in-memory catalogue and queries (category overview now; filtering, search, outside_price_range and suggestions from Phase 2)
  models.py      Pydantic response models with field descriptions
  errors.py      error envelope, CatalogError, exception handlers
  routes/        one module per tool (+ health)
tests/
  conftest.py    shared settings, catalogue and TestClient (keys: test-key, second-key)
  fixtures/      small edge-case CSVs
```

## Conventions

- All cleaning and derivation lives in `catalog_build/`, never in `app/`. The service does no data fixing at runtime.
- Never hand-edit `data/`. Change the mapping files or the build script and regenerate. `tests/test_build.py` fails if `data/catalog.json` is stale.
- `loader.py` and `catalog.py` contain no HTTP concerns; routes stay thin.
- Every route sets `operation_id` to the tool name, plus `summary` and `description`. Every `Query`/`Path` sets `description` (and `examples` where they help). `tests/test_openapi.py` enforces the descriptions.
- Errors are raised as `CatalogError(code, message, hint, ...)` and rendered by one handler. Never return a bare `HTTPException` detail.
- Do not expose raw `stock` counts. Use `availability`.
- Keep `openapi_url`, `docs_url` and `redoc_url` at their defaults, and apply auth as a dependency on the data routers (never middleware or app-wide), so the published spec stays public.
- Never declare `X-API-Key` as a header parameter on routes. Auth is a dependency; the platform sends the header from a secret, and a declared parameter would be shown to the LLM to fill in.
- No new dependency without a reason in the spec.
