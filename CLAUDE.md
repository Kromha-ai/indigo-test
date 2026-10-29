# Catalog Service — Workspace

[description]

## Projects in this workspace

- `` — 


Each project has its own `CLAUDE.md` with stack-specific commands and conventions.

---

## Operations

`PLAYBOOK.md` — first-time setup, daily workflow, running tests, and resetting the local database to stable state.

---

## Documentation index

`docs/` holds all living documents organised into four subfolders. Read the relevant document before making decisions about architecture, data model, service boundaries, or EUDR compliance logic. When a document is superseded or a roadmap phase is completed, it moves to `archive/` for historical reference.

| Folder | Purpose |
|---|---|
| `docs/planning/` | Roadmaps, improvement backlog, tracking artifacts |
| `docs/specs/` | Service specifications |
| `docs/guides/` | How-to guides, testing conventions, best practices |
| `docs/reference/` | Domain documentation, diagrams, schemas, glossary |

### planning

| Document | When to use it |
|---|---|

### specs

| Document | When to use it |
|---|---|
| `docs/specs/CATALOG_SPEC.md` | Spec for the Catalog service: product registry, field definitions, field groups, versioned data models, product profiles. |

### guides

| Document | When to use it |
|---|---|
| `docs/guides/testing.md` | Test suite overview for backend and frontend. Use when adding or reviewing tests. |
| `docs/guides/secrets-management.md` | Secret inventory, generation, storage, cross-service alignment, and rotation procedure. Read before first production deployment. |

### reference

| Document | When to use it |
|---|---|
| `docs/reference/Project_definition_v1_0.md` | Full technical and functional reference (v1.5). Start here for any question about business rules, roles, workflows, or integrations. Covers Organizations service auth delegation, Catalog service integration, and the full platform service topology. |

### Archive

`archive/` contains completed roadmaps and superseded documents kept for historical context. Do not treat these as current — they may be outdated. Reference them only to understand past decisions.

| Document | Notes |
|---|---|


---

## Domain glossary



---

## User roles



---

## Critical business rules


