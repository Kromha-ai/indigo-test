# Roadmap: Site widget

**Started**: 2026-11-01
**Specs**: `docs/specs/CATALOG_SPEC.md` · `docs/specs/AGENT_SPEC.md`

Phases 1–5 (from walking skeleton to handover) are complete and archived in `archive/roadmap-phases-1-5.md`. What remains is an optional bonus phase.

---

## Status

| Phase | Goal | Status |
|---|---|---|
| 6 (bonus) | Site widget | Not started |

---

## Phase 6 (bonus): Site widget

Goal: the assistant embedded in a web widget, as it would sit on the client's site, with formatting tuned for it.

Prerequisite: Phase 5 (done). Not needed for the handover; the shareable link is the deliverable.

- [ ] Gift Assistant **Connection**: save the recommended products in a variable, and show them through a small workflow as cards or quick replies
- [ ] Read *Configure & Install the Web Chat*: whether it adds quick-reply buttons, cards or carousels on top of Markdown, and its settings. It is embedded with `<script defer src="https://platform.indigo.ai/widget.js?token=<TOKEN>&v=3"></script>`; leave `uid` unset (anonymous shoppers)
- [ ] Decide the widget message format: quick replies for the next-step line, and cards only if they stay within one phone screen. Update `AGENT_SPEC.md` first
- [ ] Embed the widget in a minimal demo page and test it at phone width
- [ ] Re-run the NRT suite in the widget; record the results
- [ ] README: link to the demo page
