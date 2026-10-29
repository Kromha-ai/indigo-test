# Secrets Management

**Last updated**: 2026-10-29

Why the service uses static API keys in `X-API-Key`: `AUTHENTICATION.md` (repo root), *Decision record*.

---

## Inventory

| Secret | Value | Used by | Stored in | Never in |
|---|---|---|---|---|
| `CATALOG_API_KEYS` | Comma-separated list of every currently valid key | Catalog Service (validates `X-API-Key`) | `deploy/.env` on the droplet (`chmod 600`, git-ignored); local `catalog-service/.env` | Git, logs, prompts, screenshots |
| `platform-test` key | One key | indigo.ai **Test** environment | Workspace secret `CATALOG_API_KEY`, **Test** value | Tool definitions, conversations |
| `platform-prod` key | One key | indigo.ai **Production** environment | Workspace secret `CATALOG_API_KEY`, **Production** value | Tool definitions, conversations |
| `local-dev` key | One key | Local development, curl, tests against a deployed instance | Your `.env` / password manager | Anything shared |

`catalog-service/.env` is git-ignored. `catalog-service/.env.example` is committed with placeholder values only.

## Generating a key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Generate one key per row above. Never reuse a key across environments.

## Configuring the platform

1. **Workspace settings → Secrets**: create `CATALOG_API_KEY`. Set its **Test** value to the `platform-test` key and its **Production** value to the `platform-prod` key.
2. In the Catalog tool collection's headers, add `X-API-Key` with the value `[[CATALOG_API_KEY]]`, inserted with **Add secret**. The reference must be the **entire** header value. Nothing before or after it is resolved.
3. Save, test in the Test environment, then Publish the workspace.

The platform resolves the secret server-side; it never reaches the LLM, the conversation or the platform logs.

## Cross-service alignment

Every key held by the platform must be one of the values in `CATALOG_API_KEYS` on the deployed service. After any change:

- Make a tool call from the platform's Test environment and check that the service logs (`docker compose -f deploy/docker-compose.yml logs catalog-service`) show the `platform-test` key's fingerprint (the first 6 hex characters of its SHA-256) in the `key_fingerprint` field.
- After Publish, do the same from Production with the `platform-prod` fingerprint.

```bash
python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:6])" "$KEY"
```

## Rotation (zero downtime)

Example for `platform-prod`; the same steps apply to any key.

1. Generate a new key.
2. Add it to `CATALOG_API_KEYS` in `deploy/.env` on the droplet alongside the old one (`old,new`), then `docker compose -f deploy/docker-compose.yml up -d` to restart with the new environment.
3. Update the **Production** value of the `CATALOG_API_KEY` workspace secret. *To verify in Phase 1: whether a secret change takes effect immediately or needs a Publish.* Confirm that a production tool call succeeds and the logs show the new fingerprint.
4. Remove the old key from `CATALOG_API_KEYS` and restart the same way.
5. Confirm a request with the old key returns `401`.

Rotate straight away if a key appears in a commit, log, transcript or screenshot. Because each environment has its own key, a leaked test key never requires touching production.
