# Agent configuration

The indigo.ai side of the gift assistant, versioned so it can be reviewed, diffed and rebuilt. The platform is where it runs; these files are the record. The behaviour they implement is specified in `docs/specs/AGENT_SPEC.md`.

| File | What it holds |
|---|---|
| `global-settings.md` | Tone of voice, company description, Security layer settings and the workspace perimeter |
| `gift-assistant.md` | The Gift Assistant: trigger, every Agent Block section, examples, tools and settings |
| `general-agent.md` | The customised General Agent: the fallback, and the Security layer's guardrail agent for out-of-scope requests |
| `greeting.md` | Welcome message (Greeting panel) |
| `tools.md` | Step-by-step platform setup, simulation suites, and what was observed on the platform |
| `simulations.csv` | The 19 simulations (E1–E20; E14's format checks live in E1, E3, E6, E7), in the platform's import format |
| `evals.md` | Dated simulation runs |

## Live

| | |
|---|---|
| Public link | [https://clair.platform.indigo.ai/chatbot/0f86001f-e9c2-4599-9748-739a04cb16f9](https://clair.platform.indigo.ai/chatbot/0f86001f-e9c2-4599-9748-739a04cb16f9) (serves Chat bot) |
