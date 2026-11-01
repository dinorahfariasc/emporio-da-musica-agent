# Empório da Música — Melody, the customer service agent

AI customer-service agent for Empório da Música, a fictional musical instrument store in Campo
Grande/MS (Artefact AI Engineer take-home challenge, `challenge/challenge_brief.pdf`). The agent
("Melody") answers customers in Portuguese or English about the catalog, prices, order status,
store policies and return/complaint requests, backed by the store's real data and policy manual.

- **Production:** https://emporio-da-musica-agent.vercel.app
- **Backlog / scope:** [`docs/planning/backlog.md`](docs/planning/backlog.md)
- **Decisions and AI usage, in full:** [`docs/decision-log.md`](docs/decision-log.md)
- **Example conversations:** [`docs/conversations/`](docs/conversations/)
- **Data assumptions and anomalies:** [`docs/data-quality-report.md`](docs/data-quality-report.md)

## Contents

- [Architecture](#architecture)
- [Run locally](#run-locally)
- [Run in production](#run-in-production)
- [Data](#data)
- [Key decisions and trade-offs](#key-decisions-and-trade-offs)
- [AI-assistant workflow](#ai-assistant-workflow)
- [MCP server](#mcp-server)
- [Limitations and next steps](#limitations-and-next-steps)

## Architecture

```
┌─────────────┐      SSE stream       ┌──────────────────────────┐
│  Next.js     │  POST /api/chat ───▶ │  FastAPI backend          │
│  chat UI     │ ◀─── token/tool parts │                           │
│  (frontend/) │                       │  ┌─────────────────────┐ │
└─────────────┘                       │  │ router (plain Python)│ │
                                       │  │ intent classifier:   │ │
                                       │  │ decider model, Haiku │ │
                                       │  │ fallback             │ │
                                       │  └──────────┬───────────┘ │
                                       │             ▼             │
                                       │  ┌─────────────────────┐  │
                                       │  │ create_agent (per    │  │
                                       │  │ request): specialist │  │
                                       │  │ or general model,    │  │
                                       │  │ LangChain/LangGraph  │  │
                                       │  └──────────┬───────────┘  │
                                       │             ▼              │
                                       │  ┌─────────────────────┐   │
                                       │  │ tools (plain async   │   │
                                       │  │ functions, Python-   │   │
                                       │  │ computed facts):      │   │
                                       │  │ products, orders,     │   │
                                       │  │ payments, policies,   │   │
                                       │  │ actions (return,      │   │
                                       │  │ complaint, handoff)   │   │
                                       │  └──────────┬───────────┘   │
                                       └─────────────┼───────────────┘
                                                      ▼
                             ┌─────────────────────────────────────┐
                             │ Postgres (Neon) + pgvector           │
                             │ store tables (products, orders, ...) │
                             │ hybrid search index (policy chunks,  │
                             │ product docs: full-text + vectors)   │
                             └───────────────────────────────────────┘
```

- **Routing happens in plain Python, not a LangGraph node.** A request is classified by intent
  first (decider model, with a chat-model fallback), then exactly one `create_agent` run streams
  the answer with the tools for that intent. See DL-011 for why an outer graph was dropped.
- **Facts are never computed by the LLM.** Price, stock, discount eligibility and return windows
  are plain Python (`app/catalog/rules.py`, `app/policies/returns.py`); tools return JSON the model
  can only read and quote, never derive (constitution principle I).
- **Retrieval is hybrid**: Postgres full-text (`pt_unaccent`) and pgvector cosine similarity, fused
  with Reciprocal Rank Fusion, over policy chunks and per-product documents (DL-010).
- **One Vercel project, two Services** (`vercel.json`): the Next.js `frontend` is public; the
  FastAPI `backend` is private, reached only through the `BACKEND_URL` service binding.

See [`specs/002-agent-core/`](specs/002-agent-core/) for the full design (data model, contracts,
tasks) and [`specs/001-data-foundation/`](specs/001-data-foundation/) for the ETL and retrieval
index.

## Run locally

Requirements: Docker, [uv](https://docs.astral.sh/uv/), Node 24 with pnpm
(`corepack enable pnpm`).

```bash
# Database (Postgres 16 + pgvector on localhost:5433)
docker compose up -d --wait

# Backend
cd backend
cp .env.example .env
uv sync
uv run pytest
uv run uvicorn app.main:app --reload   # http://localhost:8000/api/health

# Frontend (in another terminal)
cd frontend
cp .env.example .env.local             # BACKEND_URL=http://localhost:8000
pnpm install
pnpm dev                               # http://localhost:3000/api/health
```

No API keys are needed to run the tests or try the chat UI: providers default to deterministic
fakes (`CHAT_MODE=mock` on the frontend replays fixed fixtures; the backend's fake LLM/embeddings
providers are scripted but exercise the real tool/retrieval code paths).

To use real models and embeddings locally, set in `backend/.env`:

```
LLM_PROVIDER=openrouter
ROUTER_PROVIDER=openrouter
OPENROUTER_API_KEY=...
ROUTER_MODEL=perplexity/pplx-decider-v1.2
SPECIALIST_MODEL=openai/gpt-6-luna
GENERAL_MODEL=deepseek/deepseek-v4.1-flash
EMBEDDINGS_PROVIDER=gemini
GEMINI_API_KEY=...
```

then point the frontend at the backend (`CHAT_MODE=backend` or unset) and load the catalog/policy
index (see [Data](#data) below).

Run the scripted conversation scenarios (what the example conversations are built from):

```bash
cd backend
uv run python -m evals            # fake providers, no keys
uv run python -m evals --live     # real models, needs keys above
```

## Run in production

One Vercel project using [Services](https://vercel.com/docs/services) (`vercel.json` at the repo
root): the Next.js `frontend` is the only public service; the FastAPI `backend` is private and
reached by the frontend through a service binding (`BACKEND_URL`). Postgres is Neon (São Paulo
region), connected through the Vercel Marketplace, with `DATABASE_URL` (pooled, for the app) and
`DATABASE_URL_UNPOOLED` (direct, for ETL/DDL).

Production environment variables (set in Vercel, not committed): `CHAT_MODE=backend`,
`LLM_PROVIDER=openrouter`, `ROUTER_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, `ROUTER_MODEL`,
`SPECIALIST_MODEL`, `GENERAL_MODEL`, `EMBEDDINGS_PROVIDER=gemini`, `GEMINI_API_KEY`,
`DATABASE_URL`, `DATABASE_URL_UNPOOLED`. Deploys are triggered by the repository owner; env
changes only take effect on the next redeploy.

## Data

The challenge files in `challenge/` are read-only inputs (`.gitattributes` keeps their CRLF bytes
intact). One command validates them, applies the correction rules and loads Postgres:

```bash
cd backend
uv run python -m etl            # local database from DATABASE_URL
uv run python -m etl --yes      # required for any non-local host (e.g. Neon)
```

- The seed drops and recreates only the tables it owns, in one transaction, and prints the
  target host first. Against Neon, set `DATABASE_URL_UNPOOLED` (direct endpoint); the seed
  prefers it over `DATABASE_URL`.
- Every anomaly found in the data, the rule applied and the counts are in
  [`docs/data-quality-report.md`](docs/data-quality-report.md). It is regenerated by the seed,
  and CI fails if the committed copy is stale.
- The seed also builds the search index: policy chunks from the PDF and one document per product,
  embedded with Gemini (`EMBEDDINGS_PROVIDER=gemini`, `GEMINI_API_KEY`) and stored with a
  full-text column. `EMBEDDINGS_PROVIDER=fake` (offline, deterministic) is refused for remote
  targets and production. Vectors are cached in `embedding_cache`, so re-seeding costs no calls.
  Gemini free tier: 100 requests/min, 1,000 requests/day, 30K tokens/min; Google may use
  free-tier content to improve its products, which is fine for this fictional data.
- Design: [`specs/001-data-foundation/`](specs/001-data-foundation/).

## Key decisions and trade-offs

Full context, alternatives and rationale for every decision are in
[`docs/decision-log.md`](docs/decision-log.md) (DL-001 onward). Summary of the ones the brief asks
to be justified:

| Decision | Chosen | Why (see decision log for alternatives) |
|---|---|---|
| Framework / approach | Intent router (plain Python) + one `langchain.agents.create_agent` run per request, function-calling tools, hybrid RAG for policies | A graph framework adds nothing once routing isn't itself streamed (DL-011); function calling keeps facts deterministic (constitution I); RAG scales past the current 8-page manual |
| LLM and provider | OpenRouter, one key for every model: `perplexity/pplx-decider-v1.2` (router/decider), `openai/gpt-6-luna` (specialist answers), `deepseek/deepseek-v4.1-flash` (general/ambiguous) | Measured with a 34-scenario router spike and 27-29/29 live evals (DL-012); a single provider simplifies secrets over mixing Anthropic + a dedicated decider API |
| Retrieval architecture | Postgres full-text (`pt_unaccent`) + pgvector, fused with RRF k=60; Gemini `gemini-embedding-001` embeddings, 768 dims | OR-semantics full-text keeps recall for natural-language questions without tuning; a prefix match on long lexemes fixes a stemmer gap the reference-query tests caught (DL-010) |
| Prompt strategy | System prompt carries the store's current date/time and persona (Melody, manual §7.1/§7.2); tool outputs are the only source of facts, explicitly fenced as "FATOS SOMENTE DAS FERRAMENTAS" against prompt injection | Verified by the US5 safety scenarios (prompt extraction, invented discounts, fake employee) |
| Conversation history persistence | Not implemented for P0 (each request carries its own history window from the client); durable server-side persistence is planned (P1, issue #12/S7) | The brief says to implement it only if it helps the UX; a stateless API was enough to ship P0 safely by the deadline |
| Data handling | Deterministic ETL with documented correction rules per anomaly (`docs/data-quality-report.md`), not silent cleaning | The brief explicitly flags recorded anomalies; a customer-service agent must not paper over a bad date or a contradictory product record without a visible rule |

## AI-assistant workflow

This project was built with **Claude Code**, and that usage is itself part of the deliverable: the
brief asks for the workflow to be explained, not just the fact that AI was used.

- **Spec-driven development.** Every epic goes through [Spec
  Kit](https://github.com/github/spec-kit) (`speckit-*` skills): `spec.md` → `plan.md` →
  `tasks.md` under `specs/NNN-*/`, checked against
  [`.specify/memory/constitution.md`](.specify/memory/constitution.md) (e.g. "facts are computed
  in Python, never by the LLM") before any code is written. No implementation task starts without
  an approved spec and plan.
- **Two-reviewer gate.** Every spec and every code PR gets a QA pass and a senior-engineer pass
  (both run as Claude Code subagents, prompted to find real defects, not rubber-stamp) before the
  project owner merges. Reviews are posted as a consolidated PR comment; findings and the fixes
  applied (or explicitly deferred) are recorded in the decision log — see e.g. DL-012's "Review of
  PR 1" or DL-011's "QA checked the facts against the CSVs and fixed two scenarios the data cannot
  support".
- **Parallel worktrees.** Independent tracks (data/ETL, agent core, actions, chat UI, docs) run as
  separate git worktrees/branches with their own Claude Code sessions, each scoped to its own
  files by a short brief (this README's track was "touch docs and README only"). This is why the
  decision log uses per-area prefixes (`DL-BE-`, `DL-FE-`, `DL-DOCS-`, `DL-DATA-`) once numbering
  moved off a single sequence, to avoid collisions between branches working at the same time.
- **What AI did vs. what the person decided.** Each decision-log entry ends with a "Role of AI"
  line. The recurring pattern: Claude Code drafted specs/plans/code, ran research (library
  versions, API quirks verified in a throwaway venv) and ran both review passes; the project owner
  made the model/architecture/scope calls and every merge. A concrete example: DL-011 — Claude
  Code drafted the agent-core plan and research, but the 3-PR split and model choices were the
  owner's; the senior-reviewer subagent caught three LangGraph API pitfalls (verified empirically)
  before implementation started.
- **Never attributed in commits.** Per the working agreement, no commit, PR or issue mentions
  Claude or AI assistance, and there are no `Co-Authored-By` trailers — all AI usage is documented
  here and in `docs/decision-log.md` instead, so the commit history reads as ordinary project
  history while the AI workflow is fully disclosed in the docs the brief asks for.

## MCP server

The same tools Melody uses are exposed over [MCP](https://modelcontextprotocol.io) at `/mcp`,
behind a bearer key (`MCP_API_KEY`; the server is disabled when it is unset). No business logic
lives in the MCP layer (`backend/app/mcp.py`) — it is the exact functions in
`backend/app/tools/`, wrapped only to build a per-client `ToolContext`.

Add this to Claude Desktop's `claude_desktop_config.json` (or any MCP client that supports
streamable HTTP with a bearer header):

```json
{
  "mcpServers": {
    "emporio-da-musica": {
      "url": "https://emporio-da-musica-agent.vercel.app/mcp",
      "headers": { "Authorization": "Bearer <MCP_API_KEY>" }
    }
  }
}
```

Locally: `MCP_API_KEY=dev-key uv run uvicorn app.main:app --reload`, then point a client at
`http://localhost:8000/mcp`.

## Limitations and next steps

What's known to be incomplete or weak, and what would be done with more time (full detail and
residual-risk notes are in the decision log, e.g. DL-011 "Residual risk" and DL-012 "Not applied,
on purpose"):

- **No durable conversation history.** Each request sends its own window of prior turns; nothing
  is persisted server-side across page reloads. Planned as P1 (#12/S7, Postgres checkpointer).
- **Orders are not bound to an authenticated user.** Until auth/limits (#10) land, anyone who knows
  a chat id can see the orders verified inside it, though a per-order lock (5 failed attempts, 30
  minutes) still stops guessing across chat ids. This is a known, documented residual risk, not an
  oversight.
- **No human-in-the-loop confirmation before a write action** (`request_return`,
  `register_complaint`) beyond the model asking the customer in-conversation; a hard `interrupt`
  gate is planned (P1, #13/S9).
- **No tracing/cost observability in production yet** (P1, #15/S10, Langfuse).
- **MCP server is live but needs `MCP_API_KEY` in the environment** (see above); the Claude Desktop demo (#19) is pending.
- **Return-window scenarios use the real current date**, so every dataset order is outside its
  return window today by construction (orders predate the challenge); this is a deliberate,
  documented choice (DL-002) over a configurable reference date, with a scripted-clock eval suite
  to still prove the policy logic (DL-013).
- **The final 3–5 example conversations are not fully live yet.** `docs/conversations/` has the
  selection criteria and four fake-mode placeholder transcripts (clearly marked); replacing them
  with a real `--live --export` run needs the `--export` flag added to the eval runner and the
  agent deployed with #8/#10 — tracked in `docs/delivery-checklist.md`.
- **With more time:** LLM-as-judge evals over the scenario set (P2, #22/S18), an EDA notebook
  reproducing the data-quality findings with charts (P2, #22/S17), product cards in the chat UI
  (P1, #20/S15), and the admin insights dashboard (P2, #21/E16).
