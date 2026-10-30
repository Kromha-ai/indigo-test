# PLAYBOOK

How to operate the system.

> Correct this file whenever a command changes.

---

## First-time setup

Prerequisites: Python 3.12, [uv](https://docs.astral.sh/uv/), Docker (optional, for image builds).

```bash
cd catalog-service
uv sync
cp .local.env.example .local.env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # paste into CATALOG_API_KEYS in .local.env
```

The `curl` examples below read the key from `$KEY`. Set it in each new shell:

```bash
export KEY=$(grep '^CATALOG_API_KEYS=' .local.env | cut -d= -f2 | cut -d, -f1)
```

## Daily workflow

1. Open `docs/planning/ROADMAP.md` and pick the next unchecked task.
2. If the task changes the contract (routes, parameters, response fields, descriptions, error codes), update `docs/specs/CATALOG_SPEC.md` first.
3. Run the service and try it:

   ```bash
   cd catalog-service
   uv run uvicorn app.main:create_app --factory --env-file .local.env --reload
   curl -s localhost:8000/health
   curl -s -H "X-API-Key: $KEY" localhost:8000/categories
   curl -s -H "X-API-Key: $KEY" "localhost:8000/categories/kitchen-dining/products?subcategory=Knives&max_price=100"
   curl -s -H "X-API-Key: $KEY" localhost:8000/products/HL-003
   curl -s -H "X-API-Key: $KEY" "localhost:8000/products/search?occasion=housewarming&min_price=40&max_price=60"
   ```

   Interactive docs: <http://localhost:8000/docs>. The OpenAPI document is at <http://localhost:8000/openapi.json>.

   To check the container image locally: `docker build -t catalog-service .` (from `catalog-service/`).

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

Run this after a new client export, or after changing `catalog_build/synonyms.toml` or the build script:

```bash
cd catalog-service
uv run python -m catalog_build.build_catalog
git diff --stat data/          # review what changed
```

With an unchanged export, only the build date in `BUILD_REPORT.md` changes. Otherwise read `data/BUILD_REPORT.md`: any new fixes or cross-listings need a decision before the build is committed. For a new export, also update `docs/reference/catalog-data-profile.md`.

## Deploying

Target: the DigitalOcean droplet. The service runs with Docker Compose on `127.0.0.1:8000`; the droplet's system Caddy proxies `catalog.builtbykromha.com` to it (`docs/specs/CATALOG_SPEC.md`, *Deployment*). The repo lives at `/var/www/indigo-test`; run the commands below from there.

### Every deploy

1. On the droplet: `git pull && docker compose -f deploy/docker-compose.yml up -d --build`.
2. Check the service is up and published correctly (from anywhere):

   ```bash
   curl -s https://catalog.builtbykromha.com/health        # "products_loaded": 152
   curl -s https://catalog.builtbykromha.com/openapi.json | python3 -c "import json,sys; print(json.load(sys.stdin)['servers'][0]['url'])"   # the public URL
   curl -s -o /dev/null -w '%{http_code}\n' https://catalog.builtbykromha.com/docs    # 200, no key
   ```

3. If `deploy/catalog.caddy` changed, also `sudo systemctl reload caddy`.

### Changing configuration

Edit `deploy/.env`, then `docker compose -f deploy/docker-compose.yml up -d` (Compose recreates the container with the new environment; no rebuild needed). Variables left out of `deploy/.env` take the service's defaults (see `docs/specs/CATALOG_SPEC.md`, *Configuration*).

### When something is wrong

- Logs, one JSON line per request (operation, status, latency, `error_code`, `key_fingerprint`):
  `docker compose -f deploy/docker-compose.yml logs --tail=100 catalog-service`
- **Roll back** to the previous commit, then return to `main` once fixed:

  ```bash
  git log --oneline -5                     # pick the last good commit
  git checkout <sha> && docker compose -f deploy/docker-compose.yml up -d --build
  # later, after the fix is pushed:
  git checkout main && git pull && docker compose -f deploy/docker-compose.yml up -d --build
  ```

  `git pull` does not work while a commit is checked out directly, which is why returning to `main` comes first.

## Updating the agent's tools

After any change to routes, parameters or descriptions:

1. Deploy the service.
2. Check `https://catalog.builtbykromha.com/openapi.json` shows the change.
3. Download the document: `curl -s https://catalog.builtbykromha.com/openapi.json -o openapi.json`. On the platform, open the tool collection (**Agent settings → Integrations → Tool Collections**) and re-import it from that file. Never edit names or descriptions in the form: change them in code.
4. If operations were added, assign them in the agent's **Tools** section (**+ Add tool**).
5. Re-run the evals in `agent/evals.md` in the Test environment, then **Publish** the workspace. Until then, production keeps the previous version (the card shows **Unpublished changes**).
6. Record anything non-obvious in `agent/tools.md`.

## Rotating the API key

See `docs/guides/secrets-management.md`.
