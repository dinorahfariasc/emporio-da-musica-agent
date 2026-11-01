# Delivery checklist — brief requirements vs. repo state

Cross-checked against `challenge/challenge_brief.pdf` (sections "O que você precisa construir",
"Decisões Técnicas", "Entregáveis"). Updated by Track F (#11); re-check before the tag.

_Last updated: 2026-11-01._

## 1. The agent itself

| Brief requirement | Status | Where |
|---|---|---|
| Python project | ✅ | `backend/` (FastAPI, uv, Python 3.13) |
| Assumes a persona aligned with the store | ✅ | Melody, `app/agent/prompts.py`; manual §7.1/§7.2 |
| Receives/answers messages from context | ✅ | `POST /api/chat`, SSE stream; `frontend/` chat UI |
| Knows when to query data vs. policies | ✅ | Router (`app/agent/router.py`) + tools (`app/tools/`) + hybrid retrieval (`app/retrieval/hybrid.py`) |
| Handles out-of-scope questions | ✅ | `intent=out_of_scope` path, US5 scenarios (`evals/scenarios/us5_safety.yaml`) |

## 2. Technical decisions (must be justified in README)

| Decision | Status | README section |
|---|---|---|
| Framework/approach | ✅ | "Architecture" + DL-002, DL-011 |
| Model and provider | ✅ | "Models and providers" + DL-012 |
| Interaction interface | ✅ | Next.js chat UI described in "Run locally" / "Architecture" |
| Conversation history persistence | ⚠️ partial | Per-request only; durable persistence is P1 (#12/S7), noted under "Limitations" |
| Data handling | ✅ | `docs/data-quality-report.md`, DL-001, ETL section |

## 3. Deliverables

| # | Item | Status | Where |
|---|---|---|---|
| 1 | Public GitHub repo, real commit history, no change after deadline | ⚠️ pending (user action) | Repo is private now; user makes it public and tags `v1.0-submission` at the deadline (see HANDOFF §3) |
| 2 | README.md: run instructions | ✅ | "Run locally" / "Run in production" |
| 2 | README.md: justification of decisions (framework, LLM, retrieval, prompt strategy) | ✅ | "Key decisions and trade-offs" (links to decision log) |
| 2 | README.md: known limitations + what you'd do with more time | ✅ | "Limitations and next steps" |
| 2 | README.md: AI coding assistant usage, workflow explained | ✅ | "AI-assistant workflow" (prominent section) + `docs/decision-log.md` |
| 3 | 3–5 example conversations (.md/.txt/image), ≥1 non-trivial (real-time data or policy rules) | ⚠️ template ready, **final exports pending deploy** | `docs/conversations/` — see its `README.md` for selection criteria; current files are fake-mode placeholders clearly marked, to be replaced by `python -m evals --live --export docs/conversations/` after #8/#10 land and production is live |

## 4. Known gaps / follow-ups for other tracks

- `--export` is not implemented yet in `backend/evals/__main__.py` — needs a small addition (write
  each scenario's turns + tool calls to `docs/conversations/<id>.md`) before the final export can
  run. Flagged here for whoever picks up #11 completion after #8/#10 merge; not a Track F file.
- MCP server (#8) section in the README is a placeholder marked `<!-- MCP-TRACK -->` for that
  track to fill in (server description, how to point Claude Desktop/Code at it, auth).
- The git tag `v1.0-submission` and making the repo public are the user's action, at the deadline.

## 5. Out of scope for this track

Touching `backend/`, `frontend/`, or spec files is out of scope for #11 (docs only). Any code gap
found above (e.g. `--export`) is listed, not fixed, here.
