# Empório da Música — Customer Service Agent

Artefact AI Engineer technical challenge. Customer-service agent ("Melody") for a fictional
music store. Source material lives in `challenge/` (brief, CSVs, policies PDF).

## Start here
**Read `docs/HANDOFF.md` first** (current status, environment, gotchas). Update it at the end of every session.

## Where things are
- `challenge/` — original brief and data (read-only inputs)
- `.specify/memory/constitution.md` — project principles; every spec/plan must comply
- `specs/NNN-*/` — Spec Kit artifacts per epic (spec → plan → tasks)
- `docs/decision-log.md` — running log of decisions and AI usage; **append an entry after every
  meaningful decision or phase**
- `backend/` (Python, FastAPI, LangGraph, MCP) and `frontend/` (Next.js, Vercel AI SDK) — once created

## Rules
- Workflow is Spec-Driven: no implementation without a spec + plan + tasks for the epic.
- Everything in English (code, docs, commits, PRs, issues) except the agent persona and website
  copy, which are Portuguese-first (site has a PT/EN switch; the agent replies in the user's language).
- Semantic commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`). **Never mention AI/Claude in
  commits or PRs, and never add Co-Authored-By trailers.** AI usage is documented in
  `docs/decision-log.md` instead.
- Small PRs linked to issues (`Closes #n`); the user merges.
- Prices, stock, discounts and eligibility are computed deterministically in Python — never by
  the LLM.
- Python: `uv`, `ruff`, `pytest`. Frontend: `pnpm`.
- **Keep `docs/HANDOFF.md` alive:** after every meaningful action (PR opened/merged, feature done,
  bug fixed, decision, review received, deploy), update its Status and add a short Session log
  entry (Done / Fixed / Next). No secrets. Personal skill `living-handoff` describes the routine.
