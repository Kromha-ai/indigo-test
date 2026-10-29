# PLAYBOOK

How to operate the system.

> The commands below are the target set by `docs/specs/CATALOG_SPEC.md`. They become real in roadmap Phase 1; correct this file whenever they change.

---

## First-time setup

Prerequisites: Python 3.12, [uv](https://docs.astral.sh/uv/), Docker (optional, for image builds).

```bash
cd catalog-service
uv sync
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # paste into CATALOG_API_KEYS in .env
```

## Daily workflow

1. Open `docs/planning/ROADMAP.md` and pick the next unchecked task.
2. If the task changes the contract (routes, parameters, response fields, descriptions, error codes), update `docs/specs/CATALOG_SPEC.md` first.
3. Run the service and try it:

   ```bash
   cd catalog-service
   uv run uvicorn app.main:app --reload
   curl -s localhost:8000/health
   curl -s -H "X-API-Key: $KEY" localhost:8000/categories
   curl -s -H "X-API-Key: $KEY" "localhost:8000/products/search?occasion=housewarming&min_price=40&max_price=60"
   ```

   Interactive docs: <http://localhost:8000/docs>. The OpenAPI document is at <http://localhost:8000/openapi.json>; once deployed, the platform imports it from the public URL.

4. Run the tests and lint before staging (`docs/guides/testing.md`).
5. Tick the task in the roadmap. The developer commits.

## Running tests

```bash
cd catalog-service
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Resetting to stable state

There is no database. The service loads `catalog-service/data/catalog.json` at startup, so restarting it is a full reset. If the raw export or the generated data changed by accident, restore them with `git checkout -- raw_data/ catalog-service/data/`. The raw export is never edited on purpose; the generated files are never edited by hand.

## Rebuilding the catalogue

Run this after a new client export, or after changing `catalog_catalog_build/interests.toml`, `catalog_catalog_build/synonyms.toml` or the build script:

```bash
cd catalog-service
uv run python -m catalog_build.build_catalog
git diff --stat data/          # review what changed
```

Read `data/BUILD_REPORT.md`: any new fixes, unmapped subcategories or cross-listings need a decision before the build is committed. For a new export, also update `docs/reference/catalog-data-profile.md`.

## Deploying

1. Build the image: `cd catalog-service && docker build -t catalog-service .`
2. On the host, set `CATALOG_API_KEYS` and `PUBLIC_BASE_URL` (the public HTTPS URL) as environment variables.
3. Deploy and check `GET <PUBLIC_BASE_URL>/health` reports `products_loaded: 152`.
4. Check that the OpenAPI spec is published and correct:

   ```bash
   curl -sf "$PUBLIC_BASE_URL/openapi.json" | python3 -c "import json,sys; print(json.load(sys.stdin)['servers'][0]['url'])"   # must print PUBLIC_BASE_URL
   curl -sf -o /dev/null -w '%{http_code}\n' "$PUBLIC_BASE_URL/docs"    # 200, no key
   ```

## Updating the agent's tools

After any change to routes, parameters or descriptions:

1. Deploy the service.
2. Check `$PUBLIC_BASE_URL/openapi.json` shows the change.
3. On the platform, open the tool collection (**Agent settings → Integrations → Tool Collections**) and re-import from `$PUBLIC_BASE_URL/openapi.json`. Never edit names or descriptions in the form: change them in code.
4. If operations were added, assign them in the agent's **Tools** section (**+ Add tool**).
5. Re-run the evals in `agent/evals.md` in the Test environment, then **Publish** the workspace. Until then, production keeps the previous version (the card shows **Unpublished changes**).
6. Record anything non-obvious in `agent/tools.md`.

## Rotating the API key

See `docs/guides/secrets-management.md`.
