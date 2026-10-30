# Gift Assistant: decision record

**Spec**: `docs/specs/AGENT_SPEC.md`

The *why* behind the assistant's specification. **The spec is the source of truth**: every accepted decision below is already reflected there. This file explains how it got that way, and backs up the walkthrough.

| # | Decision | Status |
|---|---|---|
| A1 | Evaluation in three layers: platform simulations, guardrails, evaluators | Accepted |

---

### A1: Evaluation in three layers

**Status**: Accepted · 2026-10-30

**Context**:

- The assistant's behaviour is specified as 18 scenarios (E1–E18). Several are hard cases that real shoppers may rarely produce: over budget, nothing suitable, out of stock, jailbreak attempts.
- The plan was to run them by hand in the platform's test chat and judge each transcript by eye.
- The indigo.ai platform offers three relevant features:
  - **Simulations**: an AI role-player plays a scripted scenario against the assistant, and a judge scores the transcript against success criteria. Runs return Pass / Fail / Error with an explanation. Simulations can be imported from CSV, grouped in suites, and the **No Regression Test (NRT)** suite gates Publish.
  - **Evaluators**: an LLM scores conversations after they end (score, label or true/false), built in or custom, with results in Analytics.
  - **Guardrails**: true/false checks on every message, live, with an action set by a Control Room rule.

**Options**:

| | Option | Assessment |
|---|---|---|
| A | Manual E1–E18 runs only | No setup, but every verdict is human judgement, regressions are found only when someone re-runs everything, and live conversations are not watched |
| B | Manual E1–E18 runs, plus evaluators and guardrails | Scenario runs scored automatically, live traffic monitored, the critical rules enforced in real time. The runs themselves are still manual |
| B, revised | **E1–E18 as platform simulations, plus evaluators and guardrails** | As B, and the scenarios run themselves: the NRT suite gates Publish and runs are comparable over time |
| C | Evaluators only | Rejected: evaluators judge conversations that already happened. Without scripted scenarios the hard cases may never be exercised before handover |

**Decision**: B, revised.

- **Simulations** implement E1–E18: 17 simulations, because E14's format criteria are part of E1, E3, E6 and E7. All 17 are in the NRT suite, with smaller suites for tool choice, hard cases, off-topic and safety, and routing.
- **Guardrails**, kept few because each adds a check to every message: hallucination and PII detection. Jailbreak attempts are stopped before any agent by the platform's Security layer, so a jailbreak guardrail would repeat the same check on every message.
- **Evaluators** monitor real conversations: chat success, AI CSAT, language coherence, repetition, plus three custom ones (recommendation format, question budget, request type).

**Consequences**:

- **Scenarios are versioned as code**: `agent/simulations.csv` in the platform's import format, edited in the repo and re-imported. The custom evaluators' prompts and the Control Room rules (the guardrails' actions) live in `agent/quality.md`; both guardrails are built in. Dated runs and fixes go in `agent/evals.md`.
- **Tool choice is checked in the Catalog Service's logs**, not by the judge. The judge may not see tool calls; every simulated conversation's calls appear in the JSON logs with `operation` and `query`.
- **LLM-judged tests can be flaky.** A failing simulation is re-run once and its transcript read before the prompt changes.
- **Guardrails cost latency** on every message. The two chosen protect hard rules that must never break in front of a shopper; anything else is left to evaluators.

**Revisit if** the judge proves unreliable on a scenario (move that check to a manual transcript review), or guardrail latency is noticeable in conversation (drop the least critical one).
