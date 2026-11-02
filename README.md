# Empório da Música — Melody, the customer service agent

AI customer-service agent for Empório da Música, a fictional musical instrument store in Campo
Grande/MS (Artefact AI Engineer take-home challenge, `challenge/challenge_brief.pdf`). The agent
("Melody") answers customers in Portuguese or English about the catalog, prices, order status,
store policies and return/complaint requests, backed by the store's real data and policy manual.

- **Production:** https://emporio-da-musica-agent.vercel.app (currently down, see
  [Run in production](#run-in-production); run it locally with Docker meanwhile)
- **Backlog / scope:** [`docs/planning/backlog.md`](docs/planning/backlog.md)
- **Decisions and AI usage, in full:** [`docs/decision-log.md`](docs/decision-log.md)
- **Example conversations:** [`docs/conversations/`](docs/conversations/)
- **Data assumptions and anomalies:** [`docs/data-quality-report.md`](docs/data-quality-report.md)

## Contents

- [Architecture](#architecture)
- [Run locally](#run-locally)
- [Run in production](#run-in-production)
- [Access for evaluators](#access-for-evaluators)
- [Data](#data)
- [Key decisions and trade-offs](#key-decisions-and-trade-offs)
- [Assumptions](#assumptions)
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

### With Docker (recommended)

Requirements: Docker. One command starts Postgres (pgvector), the FastAPI backend and the Next.js
frontend; more detail and troubleshooting in [`DOCKER.md`](DOCKER.md).

```bash
cp backend/.env.example backend/.env   # then set a real LLM provider and key (below)
docker compose up --build
```

- Frontend: http://localhost:3000 (login page)
- Backend: http://localhost:8000/api/health
- Postgres: `localhost:5433`, user/password/db `emporio`

The chat needs a real model: in `backend/.env` set `LLM_PROVIDER=openrouter`,
`ROUTER_PROVIDER=openrouter` and `OPENROUTER_API_KEY` (see [Environment variables](#environment-variables)).
`LLM_PROVIDER=fake` is a scripted model for automated tests only: in the chat every message fails.
The compose file already sets the database URL, the backend URL and dev-only secrets, so nothing
else is needed locally.

**Load the data** (first run, empty database) and **create a login** (there is no sign-up page by
design; accounts come from a CLI):

```bash
cd backend && uv sync --group etl && \
  DATABASE_URL=postgresql://emporio:emporio@localhost:5433/emporio uv run python -m etl
cd ../frontend && DATABASE_URL_UNPOOLED=postgresql://emporio:emporio@localhost:5433/emporio \
  CREATE_USER_PASSWORD='at-least-12-chars' pnpm tsx scripts/create-user.ts <username>
```

Passwords need 12+ characters. Without `CREATE_USER_PASSWORD` the script prompts for it (it is
never taken from argv). Five wrong passwords lock the account for 15 minutes.

### Without Docker

Requirements: Docker (for Postgres only), [uv](https://docs.astral.sh/uv/), Node 24 with pnpm
(`corepack enable pnpm`).

```bash
docker compose up -d --wait db           # Postgres only, localhost:5433

cd backend
cp .env.example .env                     # DATABASE_URL=...@localhost:5433/emporio
uv sync --group etl
uv run pytest
uv run uvicorn app.main:app --reload     # http://localhost:8000/api/health

cd frontend                              # another terminal
cp .env.example .env.local               # BACKEND_URL=http://localhost:8000, same SERVICE_JWT_SECRET
pnpm install
pnpm dev                                 # http://localhost:3000
```

For UI work without a backend, `CHAT_MODE=mock` on the frontend replays fixed fixtures (ignored in
production builds, which always use the backend).

### Environment variables

Templates: [`backend/.env.example`](backend/.env.example) and
[`frontend/.env.example`](frontend/.env.example). Secrets are never committed.

| Variable | Where | Local default | Production |
|---|---|---|---|
| `DATABASE_URL` | both | `postgresql://emporio:emporio@localhost:5433/emporio` (`@db:5432` inside Docker) | Neon pooled URL (Vercel Marketplace integration) |
| `DATABASE_URL_UNPOOLED` | both | same as `DATABASE_URL`; required by `create-user.ts` | Neon direct URL, for ETL/DDL and the create-user CLI |
| `SERVICE_JWT_SECRET` | both, **same value** | dev value in compose | random, 32+ chars; signs the frontend→backend token |
| `AUTH_SECRET` | frontend | dev value in compose | random, 32+ chars (Auth.js sessions) |
| `BACKEND_URL` | frontend | `http://localhost:8000` (`http://backend:8000` in Docker) | injected by the Vercel service binding (`vercel.json`) |
| `CHAT_MODE` | frontend | `backend` (`mock` = fixtures, dev only) | always `backend` |
| `ENVIRONMENT` | backend | `local` | `production` (also detected from `VERCEL_ENV`) |
| `LLM_PROVIDER`, `ROUTER_PROVIDER` | backend | must be real for chatting (`openrouter`) | `openrouter` |
| `OPENROUTER_API_KEY` | backend | your key | secret |
| `ROUTER_MODEL`, `SPECIALIST_MODEL`, `GENERAL_MODEL` | backend | see below | see below |
| `EMBEDDINGS_PROVIDER`, `GEMINI_API_KEY` | backend | `fake` is fine locally | `gemini` + key (`fake` is refused remotely) |
| `RATE_LIMIT_PER_MINUTE`, `DAILY_TOKEN_BUDGET`, `BUDGET_TIMEZONE` | backend | 20, 200000, `America/Campo_Grande` | same |
| `MCP_API_KEY` | backend | unset (`/mcp` disabled) | set to expose the MCP server |

Models used (all through OpenRouter, one key):

```
ROUTER_MODEL=perplexity/pplx-decider-v1.2
SPECIALIST_MODEL=openai/gpt-6-luna
GENERAL_MODEL=deepseek/deepseek-v4.1-flash
```

In production both apps **refuse to start** when a required variable is missing or a secret is
shorter than 32 characters (fail-closed, spec 004 FR-015): the backend checks
`SERVICE_JWT_SECRET`, `DATABASE_URL` and the provider key; the frontend checks `DATABASE_URL`,
`BACKEND_URL`, `AUTH_SECRET` and `SERVICE_JWT_SECRET`.

Run the scripted conversation scenarios (what the example conversations are built from):

```bash
cd backend
uv run python -m evals            # fake providers, no keys
uv run python -m evals --live     # real models, needs keys above
```

## Run in production

One Vercel project using [Services](https://vercel.com/docs/services) (`vercel.json` at the repo
root): the Next.js `frontend` is the only public service; the FastAPI `backend` is private and
reached by the frontend through a service binding that injects `BACKEND_URL`. `/mcp` is routed
straight to the backend. Postgres is Neon (São Paulo region), connected through the Vercel
Marketplace, which provides `DATABASE_URL` and `DATABASE_URL_UNPOOLED`.

**Status: the production deploy is currently failing and fixing it is the next step.** Since the
auth work (#44) the frontend refuses to start without its required config, and the deploy logs
show `Refusing to start in production with missing required config: BACKEND_URL`. What is known
to be missing or to check:

1. `AUTH_SECRET` and `SERVICE_JWT_SECRET` are not set in the Vercel project yet (both services
   need the same `SERVICE_JWT_SECRET`); the backend also needs `ENVIRONMENT=production` and the
   provider variables above.
2. `BACKEND_URL` comes from the service binding, so it should not be set by hand. The error
   suggests the binding is not visible when Next.js runs its startup hook
   (`src/instrumentation.ts`); to confirm on the next deploy, and if so the check should move to
   request time, as the backend already does.
3. After setting variables, redeploy: env changes only take effect on the next deploy. Then
   create the evaluator's login against Neon with `scripts/create-user.ts`
   (`DATABASE_URL_UNPOOLED` set to the Neon direct URL).

Deploys are triggered by the repository owner.

## Access for evaluators

There is no sign-up page: the agent runs on paid models, so access is by account only (spec 004).

- **Locally (works today):** `docker compose up --build` with an OpenRouter key in
  `backend/.env`, then create your own login with `scripts/create-user.ts` as shown in
  [Run locally](#run-locally). That is the whole setup.
- **Production:** once the deploy is fixed (see above), a ready account's username and password
  are sent with the delivery e-mail, never committed.
- **Without running anything:** the five live transcripts in
  [`docs/conversations/`](docs/conversations/) show each tool call and answer.

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
| Interaction interface | Web chat: Next.js (App Router) + Vercel AI SDK `useChat`, streaming tokens, tool status lines and product cards; PT/EN switch, light/dark theme, mobile-first. The same tools are also exposed over MCP | The customer channel for a store is a chat window; the UI is a thin client that only renders what the Python backend streams (no business logic, no facts derived in the UI), so Python stays the main language as the brief requires. MCP shows the tools are reusable by other agents |
| Conversation history persistence | Per browser: the conversation id and its last 40 messages live in `localStorage`, survive a reload and are cleared by "New chat" or sign-out. Every request carries the recent window (12 messages) to a stateless API; the only server-side state is the per-conversation order verification | Enough for a support chat (a reload no longer loses the context or the order verification) with no new infrastructure. Cross-device durable history (Postgres checkpointer) is a P1 (#12/S7) and not needed for the brief (DL-FE-003) |
| Access control and cost limits | Username/password login (Auth.js, accounts only from a CLI, no sign-up), a short-lived HS256 token from the frontend to the backend, 20 requests/min and 200k tokens/day per account, fail-closed config checks | The agent runs on paid models behind a public URL; the brief's evaluator needs a login, not open access (spec 004, DL-BE-002, DL-FE-001) |
| Stock answers | Tools return the exact `stock_quantity`; `get_product(quantity=N)` returns `enough_stock` computed in Python | The agent must say with certainty whether N units are available, never send the customer to check (DL-BE-003) |
| Local runtime | Docker Compose with Postgres, backend and frontend; the backend reads `backend/.env` for the provider key | Whoever clones the repo runs everything with one command and one key |
| Data handling | Deterministic ETL with documented correction rules per anomaly (`docs/data-quality-report.md`), not silent cleaning | The brief explicitly flags recorded anomalies; a customer-service agent must not paper over a bad date or a contradictory product record without a visible rule |

## Assumptions

Where the brief or the data were silent, these interpretations were taken (each one has a
decision-log entry with the reasoning):

- **"Today" is the real current date** in Campo Grande (America/Campo_Grande). Return windows and
  "open now" are computed from it, so every order in the dataset is outside its return window;
  the policy logic is still proven by a scripted-clock eval suite (DL-002, DL-013).
- **The agent informs, it does not sell.** It never places orders or reservations; it points to
  the website, the store or WhatsApp. It can register a return request, a complaint
  or a human handoff, and only on the customer's explicit request.
- **The store sells instruments only.** Accessories (strings, picks, cables, cases, pedals,
  amplifiers) are refused politely, with an instrument suggested instead.
- **Order data needs proof of ownership:** order number plus the e-mail or phone on file, with a
  generic error on mismatch and a lock after repeated failures (privacy, manual §9).
- **Data anomalies are corrected by explicit rules, not silently** (e.g. a product name beats a
  contradicting description; only four promotions are active), listed in
  `docs/data-quality-report.md` (DL-001).
- **Replies follow the customer's language** (Portuguese by default, English and Spanish
  supported); the policy manual is searched in Portuguese.
- **Access is by account and usage is capped** (20 messages/min, 200k tokens/day per account),
  because the deployed agent runs on paid models behind a public URL.
- **Stock answers are exact:** the agent states the quantity on hand and whether N units can be
  sold, from the database (DL-BE-003).

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

- **History is per browser.** The conversation survives a reload but not a change of device or
  browser; server-side history is a P1 (#12/S7, Postgres checkpointer).
- **Production deploy is down** (see [Run in production](#run-in-production)); the full stack runs
  locally with Docker.
- **Budget is soft under concurrency.** Two simultaneous requests can both pass the daily token
  check before either records usage, so an account can briefly exceed 200k tokens; the per-minute
  limit bounds the overshoot (documented in `specs/004-auth-limits-deploy/contracts/`).
- **No human-in-the-loop confirmation before a write action** (`request_return`,
  `register_complaint`) beyond the model asking the customer in-conversation; a hard `interrupt`
  gate is planned (P1, #13/S9).
- **No tracing/cost observability in production yet** (P1, #15/S10, Langfuse).
- **MCP server is live but needs `MCP_API_KEY` in the environment** (see above); the Claude Desktop demo (#19) is pending.
- **Return-window scenarios use the real current date**, so every dataset order is outside its
  return window today by construction (orders predate the challenge); this is a deliberate,
  documented choice (DL-002) over a configurable reference date, with a scripted-clock eval suite
  to still prove the policy logic (DL-013).
- **Example conversations were recorded by hand-driving the API**, not exported by the eval
  runner; an `--export` flag would make them regenerable in one command.
- **With more time:** LLM-as-judge evals over the scenario set (P2, #22/S18) and the admin
  insights dashboard (P2, #21/E16). The EDA notebook with the data-quality findings is already in
  `analysis/` (#22/S17).
