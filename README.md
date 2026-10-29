# Gift Shop Catalog Service and Gift Assistant

A product discovery assistant for an online gift shop. The shop's CSV catalogue export is served as an authenticated FastAPI service. Its OpenAPI specification becomes a tool collection for a gift assistant built on the indigo.ai platform.

| | |
|---|---|
| Live assistant | *added in Phase 4* |
| API base URL | `https://catalog.builtbykromha.com` (live from Phase 1) |
| OpenAPI spec (public) | `https://catalog.builtbykromha.com/openapi.json` · Swagger UI `/docs` · ReDoc `/redoc` |
| Authentication | `X-API-Key` header on every data endpoint; `/openapi.json`, `/docs`, `/redoc` and `/health` are public. How to authenticate, and why: `AUTHENTICATION.md` |

## Where to look

- **The problem**: `docs/reference/scenario.md`
- **What the data really contains**: `docs/reference/catalog-data-profile.md`
- **API contract and design decisions**: `docs/specs/CATALOG_SPEC.md`
- **Assistant behaviour and evaluation**: `docs/specs/AGENT_SPEC.md`
- **Progress**: `docs/planning/ROADMAP.md`
- **How to authenticate**: `AUTHENTICATION.md`
- **Run it locally**: `PLAYBOOK.md`
- **How we work**: `WORKFLOW.md`

## The assistant

*Written in Phase 5, from `docs/specs/AGENT_SPEC.md` and `agent/`.*

### The prompt

### How the tools are bound to the agent

### Conversation design decisions

- How many questions before recommending, and why
- The recommendation message: products per message, fields, format, next step
- The hard cases: vague, specific, over budget, nothing suitable, out of stock, off-topic
