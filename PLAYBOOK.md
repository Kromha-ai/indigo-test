# PLAYBOOK

How to operate the system.

> Correct this file whenever a command changes.

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
   uv run uvicorn app.main:create_app --factory --env-file .env --reload
   curl -s localhost:8000/health
   curl -s -H "X-API-Key: $KEY" localhost:8000/categories
   curl -s -H "X-API-Key: $KEY" "localhost:8000/products/search?occasion=housewarming&min_price=40&max_price=60"
   curl -s -H "X-API-Key: $KEY" "localhost:8000/categories/kitchen-dining/products?subcategory=Knives&max_price=100"
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

Run this after a new client export, or after changing `catalog_build/synonyms.toml` or the build script:

```bash
cd catalog-service
uv run python -m catalog_build.build_catalog
git diff --stat data/          # review what changed
```

Read `data/BUILD_REPORT.md`: any new fixes or cross-listings need a decision before the build is committed. For a new export, also update `docs/reference/catalog-data-profile.md`.

## Deploying

Target: the DigitalOcean droplet, Docker Compose behind Caddy (`docs/specs/CATALOG_SPEC.md`, *Deployment*, decision D4).

### First time on the droplet

1. DNS: create an A record for `catalog.builtbykromha.com` pointing at the droplet's IP. Check with `dig +short catalog.builtbykromha.com` before starting Caddy; otherwise the certificate request fails and Let's Encrypt rate-limits retries.
2. Firewall: allow only 22, 80 and 443 (DigitalOcean Cloud Firewall or `ufw allow OpenSSH && ufw allow 80,443/tcp && ufw enable`).
3. Install Docker Engine and the Compose plugin; clone the repo as the deploy user.
4. `cp deploy/.env.example deploy/.env && chmod 600 deploy/.env`. Set `CATALOG_API_KEYS` and `PUBLIC_BASE_URL=https://catalog.builtbykromha.com`. The domain is already in `deploy/Caddyfile`.
5. `docker compose -f deploy/docker-compose.yml up -d --build`. Caddy fetches the certificate on first start.

### Every deploy

1. On the droplet: `git pull && docker compose -f deploy/docker-compose.yml up -d --build`.
2. Check `GET $PUBLIC_BASE_URL/health` reports `products_loaded: 152`.
3. If something is wrong: `docker compose -f deploy/docker-compose.yml logs --tail=100 catalog-service`. To roll back, `git checkout <previous-sha>` and run step 1 again.
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
