# Implementation Plan: Auth, limits, cost controls and production deploy

**Branch**: `004-auth-limits-deploy` | **Date**: 2026-11-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-auth-limits-deploy/spec.md`

## Summary

Replace the `/login` placeholder with real credential-based login (Auth.js, JWT session
strategy) backed by a `users` table in the existing Neon Postgres database, provisioned only via
a CLI script (no public sign-up). The Next.js BFF route handler that already proxies
`POST /api/chat` to FastAPI (`frontend/src/app/api/chat/route.ts`) is extended to: require an
Auth.js session (via middleware), mint a short-lived HS256 service JWT identifying the account,
and forward it to the backend. FastAPI verifies that JWT, then enforces a per-account 20 req/min
rate limit and a 200k-token/day budget (America/Campo_Grande reset) using two small Postgres
tables, before running the agent; actual token usage from the finished turn is recorded back.
Both services fail closed on missing/invalid required production config. Deploy wiring (env vars,
DB migration, CLI run, Anthropic/OpenRouter workspace spend cap) is documented for the user to
execute.

## Technical Context

**Language/Version**: TypeScript (Next.js 16, Node runtime) for the BFF/auth; Python 3.13
(FastAPI) for limits enforcement and verification — both already the project's languages.

**Primary Dependencies**: `next-auth` (Auth.js) v5 credentials provider + `jose` (JWT mint) on the
frontend; `PyJWT` (JWT verify) on the backend. `bcryptjs` (pure-JS, no native build step — safe on
Vercel Functions) for password hashing, used by both the Next.js login path and the Node
`create-user` CLI script. No new database technology — same Neon Postgres already used for
retrieval/orders (`backend/app/db.py`).

**Storage**: Neon Postgres (existing). Three new tables: `users`, `rate_limit_minute`,
`token_usage_daily` (see `data-model.md`). No ORM is introduced; the frontend uses a tiny `pg`
client for the three statements it needs (credential lookup, nothing else); the backend uses the
existing `psycopg` pool.

**Testing**: `pytest` (backend: JWT verification, rate/budget enforcement, fail-closed config —
fake clock, no real Postgres needed for unit tests, a docker-compose integration test for the
atomic counters) and `vitest` (frontend: `authorize()` credential check, service-JWT minting,
middleware redirect) — both already the project's test runners.

**Target Platform**: Vercel (Next.js + Python Functions), as the rest of the project.

**Project Type**: Web application (existing `backend/` + `frontend/` split).

**Performance Goals**: Login and the auth/limit checks must not be user-perceptible — under 100ms
added latency before the agent turn starts (the turn itself already runs seconds behind an LLM
call). No specific throughput target: this is a single-reviewer deployment (see spec Assumptions).

**Constraints**: Fail closed (spec FR-015): any required secret/config missing or invalid in
`Environment.PRODUCTION` must stop requests from being served rather than silently allow them.
Service JWT must be short-lived (minutes). No native/compiled Node dependency (Vercel Functions
bundle constraint already documented in HANDOFF gotchas).

**Scale/Scope**: One to a handful of named accounts (spec Assumptions); counters sized
accordingly — no need for a distributed rate limiter, a plain Postgres row per account per
minute/day is enough.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How this feature complies |
|---|---|
| I. Facts from the system, never the model | Rate/budget decisions and eligibility to proceed are computed in Python from Postgres counters; the LLM is never asked whether a request is allowed. |
| II. LLM only where it adds value | Not touched by this feature (no new LLM calls; limits are pure Python/SQL). |
| III. Clean, traceable data | New tables are migrations with explicit schema (`data-model.md`); no ETL/CSV involved. |
| IV. Tested before done | Unit tests for JWT verify, limit math (fake clock, day-boundary edge case), fail-closed startup check; a regression test for any bug found. No paid LLM calls needed to test this feature. |
| V. Safe and respectful to the customer | This feature *is* principle V's enforcement: auth required, per-user token budget, rate limit, no credential ever reaches the agent/LLM layer, secrets never logged (reuse `mask_pii` conventions for any logged identifiers). |
| VI. Simple, modular, replaceable | Auth.js and the service-JWT check sit behind the existing BFF boundary; the backend gains one dependency (`require_service_account`) other routes can reuse later; no abstraction beyond the three tables and two dependencies needed now. |

No violations requiring `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/004-auth-limits-deploy/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   ├── service-jwt.md             # BFF → backend auth contract
│   ├── rate-limit-and-budget.md   # 429 response shape, headers, reset semantics
│   └── create-user-cli.md         # CLI usage contract
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py              # + service_jwt_secret, rate_limit_per_minute, daily_token_budget,
│   │                           #   budget_timezone; fail-closed validation
│   ├── auth/                   # NEW
│   │   ├── __init__.py
│   │   ├── schema.sql          # users, login_attempts (idempotent CREATE TABLE IF NOT EXISTS,
│   │   │                       #   same pattern as app/agent/schema.sql)
│   │   ├── service_jwt.py      # verify_service_jwt(token) -> AccountClaims | raises
│   │   └── dependency.py       # FastAPI dependency: require_service_account
│   ├── limits/                 # NEW
│   │   ├── __init__.py
│   │   ├── schema.sql          # rate_limit_minute, token_usage_daily (same idempotent pattern)
│   │   ├── store.py            # Postgres reads/writes for the two counter tables
│   │   └── enforce.py          # check_and_increment_rate(), check_budget(), record_usage()
│   ├── agent/
│   │   ├── schema.sql          # EDIT: conversation_state gets `user_id`, PK becomes (user_id, conversation_id)
│   │   └── state.py            # EDIT: get/reserve_attempt/etc. take the account id (FR-009a, R10)
│   ├── api/
│   │   └── chat.py            # + Depends(require_service_account), + limit checks before the
│   │                           #   agent runs, + record_usage() after it finishes, + pass account
│   │                           #   id into every app.agent.state call
└── tests/
    ├── auth/test_service_jwt.py
    ├── limits/test_enforce.py
    ├── agent/test_state_scoping.py    # two accounts, one conversation id, no cross-visibility
    └── api/test_chat_auth_and_limits.py

frontend/
├── auth.ts                     # NEW: Auth.js config (Credentials provider, JWT session)
├── middleware.ts               # NEW: redirect unauthenticated requests to /login
├── scripts/
│   └── create-user.ts          # NEW: CLI, reads DATABASE_URL_UNPOOLED, hashes, inserts
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth/[...nextauth]/route.ts   # NEW: Auth.js route handler
│   │   │   └── chat/route.ts                 # EDIT: require session, mint + forward service JWT
│   │   └── login/page.tsx                    # EDIT: real credentials form (was placeholder)
│   ├── components/login/
│   │   ├── login-notice.tsx                  # EXISTING, kept
│   │   └── login-form.tsx                    # NEW
│   └── lib/
│       └── auth/
│           ├── db.ts            # tiny pg client, single credential-lookup query
│           └── service-jwt.ts   # mint a short-lived JWT with `jose`
└── test/
    ├── auth/service-jwt.test.ts
    └── auth/middleware.test.ts
```

**Structure Decision**: extends the existing `backend/` + `frontend/` split; no new top-level
project. Auth/limits logic is isolated in two new backend packages (`app/auth`, `app/limits`) and
one new frontend concern (`auth.ts` + `src/proxy.ts` + `lib/auth/`), matching the "thin provider
interface" style already used for LLM/embeddings providers (constitution VI).

## Complexity Tracking

*No constitution violations — table omitted.*
