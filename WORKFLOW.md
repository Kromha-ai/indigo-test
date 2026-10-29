# Development Workflow

This document explains how we write, structure, and use documentation in this project, and how that documentation drives implementation.

---

## Core principle: spec before code

Every new service, major feature, or cross-service integration starts with a written document — not a branch. The spec is the decision record, the API contract, and the acceptance criteria rolled into one. Code follows the spec; the spec does not describe code that already exists.

The workflow has three stages:

```
1. Specify  →  2. Plan  →  3. Implement & Ship
   docs/specs/    docs/planning/    (code + tests)
                                        ↓
                               archive/ (on completion)
```

---

## Documentation structure

```
docs/
├── specs/       ← What we are building (contracts, data models, API surfaces)
├── planning/    ← How we are building it (roadmaps, phases, task lists)
├── guides/      ← How to operate it (testing, secrets, backup)
└── reference/   ← What we built (domain truth, schemas, architecture)

archive/         ← Completed roadmaps and superseded documents
```

Each folder has a distinct job. The rule of thumb: if you are deciding something, write it in `specs/` or `planning/`. If you are documenting something that is already true, write it in `reference/` or `guides/`.

### `docs/specs/` — Service specifications

A spec defines a service or subsystem before a single line is written. It captures:

- Purpose and goals (and explicit out-of-scope items)
- Data model (entities, fields, relationships, constraints)
- API surface (endpoints, request/response shapes, auth requirements)
- Business rules and invariants
- Inter-service dependencies

A spec carries a `Status` field at the top:

| Status | Meaning |
|---|---|
| `Draft` | Work in progress — not ready for implementation |
| `Approved` | Signed off — implementation can begin |
| `Implemented` | Code ships; spec is the living contract |

Specs do not move to `archive/` when a service ships — they stay in `docs/specs/` as the living API contract. They are updated whenever the service evolves.


### `docs/planning/` — Roadmaps and phase tracking

A roadmap breaks a spec (or a cross-service integration) into ordered, checkable phases. Each phase is small enough to ship independently and contains a concrete task list.

Roadmaps are working documents — they track in-progress state during development. Once a phase ships, its tasks are checked off. Once an entire roadmap is complete, it moves to `archive/` and the planning document is updated to point there.


### `docs/guides/` — Operational how-tos

Guides document how to do recurring operational tasks: running the test suite, generating secrets, restoring a database backup, writing E2E tests. They are not project-specific timelines — they are stable procedures that stay relevant across phases.


### `docs/reference/` — Domain truth

Reference documents describe the system as it is, not as we plan to build it. They are the authoritative source for business rules, domain entities, schemas, and architecture diagrams.


### `archive/` — Completed work

When a roadmap phase (or an entire roadmap) ships, it is moved here. Archive documents are kept for historical context — to understand why a decision was made — but they are not current. Do not treat them as active guidance.

---

## The spec-driven development cycle

### Step 1 — Write the spec

Before opening a branch or writing a migration, produce a spec in `docs/specs/`. The spec must answer:

- What problem does this solve?
- What entities and fields does it introduce?
- What is the API surface? (HTTP verbs, routes, request/response bodies, status codes)
- What are the business rules and invariants?
- What other services does this depend on, and how?
- What is explicitly out of scope?

A spec is ready to be marked `Approved` when:
- All inter-service dependencies are resolved or noted as assumptions
- There are no open questions that would block implementation
- The data model is specific enough to write a migration from

### Step 2 — Write the roadmap

With an approved spec, write (or add a phase to) a roadmap in `docs/planning/`. Break the work into phases of roughly one to three days each. Every phase should produce a shippable slice — no phase ends with the system in a broken state.

Each phase lists:
- A clear goal (one sentence)
- A numbered or bulleted task list granular enough to track progress
- Any prerequisite phases or external dependencies

### Step 3 — Implement phase by phase

Work through the roadmap top-to-bottom, one phase at a time. As tasks complete, check them off in the roadmap. Do not skip phases to get to an interesting problem — phases are ordered to keep the system in a working state throughout development.

Implementation follows the spec. If you discover the spec is wrong or incomplete, update the spec first, then adjust the code. The spec is the source of truth; code is its expression.

### Step 4 — Write tests alongside the code

Every new endpoint or business-rule change ships with tests. The spec gives you the acceptance criteria; the test proves the code meets them.

For new services, integration tests against the real data (here, the client's CSV) are preferred over unit tests with mocks — the spec contract is at the HTTP boundary, so test at the HTTP boundary.

**A bug fix ships with a test too**, and that test must fail without the fix. A fix nobody can
reproduce is a fix nobody can keep: the next refactor reintroduces it silently. Write the test
first if you can — it is the cheapest proof you have understood the bug rather than a symptom of it.

**Prove the test is load-bearing before you trust it.** Revert the fix (`git stash push <file>`),
run the test, watch it fail, restore. A test that passes both with and without the change is
telling you nothing, and it is easy to write one by accident — a selector that matches nothing, an
assertion on a value that was already correct, a mock that answers before the code under test runs.
Reading the output carefully matters as much: a suite that prints `1 failed` above `12 passed` has
failed.

**Drive the real path when the risk is in the wiring.** Unit tests prove a function's logic; they
cannot see a queue nobody consumes, a response envelope the client reads from the wrong key, or an
endpoint that answers 500 for one role. Those live between components, and only exercising the path
end to end finds them.

**Leave the database as you found it.** Probing a live service creates real rows. Delete what you
made and verify it is gone; a stray fixture becomes someone else's confusing bug report.

### Step 5 — Archive and update reference

When a roadmap is fully complete:
1. Move it to `archive/` with a note of the completion date.
2. Update `docs/planning/ROADMAP.md` (or the relevant active roadmap) to point to the archive and mark the phase complete.
3. Update `CLAUDE.md` (glossary, critical business rules) if the shipped work changes any business rules, entities, or workflows.
4. Update `docs/reference/catalog-data-profile.md` if a new catalogue export was received.

---

## How to navigate the docs for a given task

| Task | Start here |
|---|---|
| Working on a new service | `docs/specs/` — write the spec first |
| Continuing an in-progress phase | `docs/planning/` — open the active roadmap |
| Understanding the client's problem | `docs/reference/scenario.md` |
| Understanding a business rule or domain term | `CLAUDE.md` (glossary, critical business rules) |
| Understanding the raw data | `docs/reference/catalog-data-profile.md` |
| Changing agent behaviour | `docs/specs/AGENT_SPEC.md` · `agent/evals.md` |
| Writing tests | `docs/guides/testing.md` |
| Fixing a bug | Write the failing test first, then Step 4 above |
| Setting up the local environment | `PLAYBOOK.md` |
| Deploying or rotating secrets | `PLAYBOOK.md` · `docs/guides/secrets-management.md` |

---

## Conventions

**Specs and reference docs stay in `docs/`.** They are updated in place as the system evolves. They do not move to `archive/` just because a phase shipped — they are living documents.

**Roadmaps move to `archive/` when complete.** Active planning documents point to the archive location. This keeps `docs/planning/` small and focused on what is actually in progress.

**`CLAUDE.md` is the AI collaboration contract.** It lists the documentation index and critical business rules that must be read before making architectural decisions. Keep it in sync with what is in `docs/`.

**One spec per service.** Do not split a service spec across multiple files. If a service grows large, add sections to the existing spec rather than creating parallel documents.

**Only the developer commits and pushes.** The developer is the only one who writes commit messages, creates commits, and pushes to any remote. AI assistants and other collaborators may stage changes and propose a commit message, but must never run `git commit`, `git push`, or anything else that creates commits or rewrites history (amend, rebase, merge commits).

**Absolute dates in planning documents.** Write `2026-06-01` rather than "next Thursday" — relative dates rot immediately. Reference docs and archive documents include the date of last material update.
