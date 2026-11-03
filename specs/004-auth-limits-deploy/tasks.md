---

description: "Task list for 004-auth-limits-deploy"
---

# Tasks: Auth, limits, cost controls and production deploy

**Input**: Design documents from `/specs/004-auth-limits-deploy/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: included — constitution IV ("Tested before done") is non-negotiable for this project,
and the merged spec's FR-020 explicitly requires automated coverage of every path here with no
paid service calls.

**Organization**: tasks are grouped by user story (spec.md priorities). US1–US4 are all P1; a
usable MVP needs **US1 + the Foundational phase** (login works, but with no limits and no
conversation fix, it is not safe to deploy — US3 and US4 are both required before production per
spec constitution-V framing, so the realistic MVP for *this feature* is US1–US4 together). US5
(fail-closed config) and Polish (deploy) close it out.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no unmet dependency)
- **[Story]**: US1 (login), US2 (create-user CLI), US3 (rate/budget limits), US4 (conversation
  ownership), US5 (fail-closed config)

---

## Phase 1: Setup

- [ ] T001 Add backend dependency `PyJWT>=2.9` to `backend/pyproject.toml` `[project.dependencies]`; run `uv sync`.
- [ ] T002 [P] Add frontend dependencies `next-auth@beta` (v5), `jose`, `bcryptjs`, `@types/bcryptjs`, `pg`, `@types/pg`, and dev dependency `tsx` to `frontend/package.json`; run `pnpm install`.
- [ ] T003 [P] Add `SERVICE_JWT_SECRET` and `AUTH_SECRET` to `backend/.env.example` and `frontend/.env.example` with one-line comments on what each is and that they must match the project's local dev values, not production's.
- [ ] T004 [P] Add `rate_limit_per_minute` (default 20), `daily_token_budget` (default 200000), and `budget_timezone` (default `"America/Campo_Grande"`) as configurable fields (FR-013: "configurable without code changes") on `Settings` in `backend/app/config.py`, alongside the existing `service_jwt_secret: str | None = None` field.

**Checkpoint**: dependencies installed, env vars documented, settings extended — no behavior changed yet.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the service-JWT verification dependency and the new tables that every user story
needs. No user story can be implemented or tested before this phase is done.

- [ ] T005 [P] Create `backend/app/auth/__init__.py` and `backend/app/auth/schema.sql` with `CREATE TABLE IF NOT EXISTS users (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), username text UNIQUE NOT NULL, password_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), disabled_at timestamptz)` and `CREATE TABLE IF NOT EXISTS login_attempts (username text PRIMARY KEY, failed_count int NOT NULL DEFAULT 0, window_start timestamptz NOT NULL DEFAULT now())`, following the comment/idempotency style of `backend/app/agent/schema.sql` (data-model.md).
- [ ] T006 [P] Create `backend/app/limits/__init__.py` and `backend/app/limits/schema.sql` with `CREATE TABLE IF NOT EXISTS rate_limit_minute (user_id uuid NOT NULL, window_start timestamptz NOT NULL, request_count int NOT NULL DEFAULT 0, PRIMARY KEY (user_id, window_start))` and `CREATE TABLE IF NOT EXISTS token_usage_daily (user_id uuid NOT NULL, usage_date date NOT NULL, tokens_used int NOT NULL DEFAULT 0, PRIMARY KEY (user_id, usage_date))` (data-model.md).
- [ ] T007 Add `ensure_auth_tables(conn)` to `backend/app/auth/schema.py` (new file, mirrors `ensure_agent_tables` in `backend/app/agent/state.py`: advisory-lock, read+execute `schema.sql`, commit) and `ensure_limit_tables(conn)` to `backend/app/limits/schema.py` likewise.
- [ ] T008 In `backend/app/agent/schema.sql`, change `conversation_state` from `conversation_id text PRIMARY KEY` to add `user_id uuid NOT NULL` and `PRIMARY KEY (user_id, conversation_id)` (FR-009a, data-model.md "Conversation scoping"); since no production conversations exist yet, this is a direct schema edit, not a backfill migration.
- [ ] T009 [US-shared] Update every function in `backend/app/agent/state.py` (`get`, `reserve_attempt`, and any sibling verify/lock function) to take a `user_id: str` parameter and include it in every `WHERE`/`INSERT` touching `conversation_state`, so a lookup or write for `(user_id=A, conversation_id=C)` never reads or writes `(user_id=B, conversation_id=C)`'s row.
- [ ] T010 [P] Create `backend/app/auth/service_jwt.py`: `verify_service_jwt(token: str, secret: str) -> AccountClaims` using `PyJWT`, checking signature (HS256), `exp` (reject if expired beyond 30s leeway — `jwt.decode(..., leeway=30)`), and required claims `sub`/`username`; raise a dedicated `InvalidServiceToken` exception on any failure (contracts/service-jwt.md).
- [ ] T011 Create `backend/app/auth/dependency.py`: FastAPI dependency `require_service_account(request, settings=Depends(get_settings)) -> AccountClaims` that: returns `500` if `settings.service_jwt_secret` is falsy (fail closed, FR-015, contracts/service-jwt.md); returns `401 unauthorized` (existing chat error shape, `http-401.json`) if the `Authorization` header is missing/malformed or `verify_service_jwt` raises; otherwise returns the claims.
- [ ] T012 [P] [Foundational] Write `backend/tests/auth/test_service_jwt.py`: valid token round-trip, expired token rejected, token rejected just past the 30s leeway, tampered signature rejected, missing `sub` rejected.
- [ ] T013 [P] [Foundational] Write `backend/tests/auth/test_dependency.py`: missing secret → 500; missing header → 401; bad bearer format → 401; valid token → claims returned.
- [ ] T014 [P] [Foundational] Write `backend/tests/agent/test_state_scoping.py`: verifying order X under `(user_a, conv_c)` then reading `(user_b, conv_c)` returns unverified state (FR-009a, SC-007).
- [ ] T015 Wire `require_service_account` into `backend/app/api/chat.py` as a `Depends(...)` on the `POST /api/chat` route, and thread the returned `user_id` through to every `app.agent.state` call already present in that handler (replacing the bare `conversation_id` calls changed in T009).

**Checkpoint**: backend now rejects every `/api/chat` request without a valid service JWT, and
conversation state is account-scoped. Nothing can call it successfully yet — the frontend does not
mint tokens. This is expected; US1 closes that gap next.

---

## Phase 3: User Story 1 - An reviewer logs in and chats (Priority: P1) 🎯 MVP start

**Goal**: real credentials login replaces the `/login` placeholder; a signed-in session is required
to reach the chat and to get a working answer.

**Independent Test**: with no session cookie, visiting `/` redirects to `/login`; signing in with a
provisioned account reaches the chat and a message gets a real streamed answer; a wrong password is
refused generically; reload keeps the session; sign-out ends it.

- [ ] T016 [P] [US1] Create `frontend/src/lib/auth/db.ts`: a tiny `pg` `Pool` (lazy singleton, same spirit as `backend/app/db.py`) over `process.env.DATABASE_URL`, exposing `findUserByUsername(username: string)` returning `{id, username, passwordHash, disabledAt} | null`.
- [ ] T017 [US1] Create `frontend/src/lib/auth/lockout.ts`: `recordFailedAttempt(username)` and `isLockedOut(username)` against the `login_attempts` table — 5 failures within 15 minutes locks further attempts for that username for 15 minutes (FR-005, R11); `clearAttempts(username)` called on successful login.
- [ ] T018 [US1] Create `frontend/auth.ts`: Auth.js v5 config, Credentials provider, JWT session strategy, `session.maxAge` 30 days; `authorize({username, password})` calls `isLockedOut` first (reject generically if locked), then `findUserByUsername`, rejects if not found/disabled/wrong password (via `bcryptjs.compare`) with one generic error, calls `recordFailedAttempt` on any failure and `clearAttempts` on success, returns `{id, name: username}` on success.
- [ ] T019 [US1] Create `frontend/src/app/api/auth/[...nextauth]/route.ts` exporting the Auth.js `GET`/`POST` handlers built from `auth.ts`.
- [ ] T020 [US1] Create `frontend/src/proxy.ts`: redirect any request for a protected path (the chat page; everything except `/login` and the Auth.js routes) with no valid session to `/login?callbackUrl=<original path>`, accepting `callbackUrl` only when it is a same-site relative path (reject absolute/external URLs).
- [ ] T021 [US1] Create `frontend/src/components/login/login-form.tsx`: username + password fields, submits via Auth.js `signIn("credentials", ...)`, shows the generic error message on failure, redirects to `callbackUrl` (or `/`) on success.
- [ ] T022 [US1] Edit `frontend/src/app/login/page.tsx`: replace the placeholder paragraph with `<LoginForm />`, keep the existing `<LoginNotice />` (reused as-is for the `reason=expired` case per `research.md` R8), remove the "Placeholder until auth (#10)" comment.
- [ ] T023 [US1] Add a sign-out control (e.g. in the chat header/shell) that calls Auth.js `signOut()`.
- [ ] T024 [US1] Create `frontend/src/lib/auth/service-jwt.ts`: `mintServiceJwt(userId, username, secret)` using `jose`'s `SignJWT`, HS256, `exp` = now + 120s (contracts/service-jwt.md).
- [ ] T025 [US1] Edit `frontend/src/app/api/chat/route.ts`: before proxying, require an Auth.js session (401 `unauthorized`, matching `http-401.json`, if absent); re-check the account's `disabled_at` via `findUserByUsername` and 401 if disabled (data-model.md note); mint the service JWT and send it as `Authorization: Bearer <token>` to the backend; if `SERVICE_JWT_SECRET` is unset, fail the request with 500 rather than sending an unsigned/placeholder token (R4, FR-015).
- [ ] T026 [P] [US1] Write `frontend/test/auth/service-jwt.test.ts`: minted token has `sub`, `username`, `exp - iat === 120`, verifies with the matching secret.
- [ ] T027 [P] [US1] Write `frontend/test/auth/lockout.test.ts` (fake clock / injected `now()`): 5 failures lock the 6th attempt; the lock clears after 15 minutes; a successful login clears the counter.
- [ ] T028 [P] [US1] Write `frontend/test/auth/middleware.test.ts`: unauthenticated request to a protected path redirects to `/login?callbackUrl=...`; an absolute/external `callbackUrl` is rejected/ignored; an authenticated request passes through; `/login` itself redirects away when already signed in (Edge Cases).
- [ ] T029 [US1] Create `frontend/scripts/create-user.ts` with a minimal placeholder sufficient only for T016–T028's manual verification (full CLI contract is US2, T030) — **may be skipped if T030 is done first**; note left here only to flag the dependency, no separate task body needed.

**Checkpoint**: an account created directly in the database can sign in, reach the chat, and get a
real answer; wrong password/lockout/redirect/session/sign-out all behave per spec. (Account
creation itself still requires a manual `INSERT` until US2 lands.)

---

## Phase 4: User Story 2 - The project owner provisions an reviewer account (Priority: P1)

**Goal**: a CLI creates accounts; there is no other way to create one.

**Independent Test**: run the CLI with a username/password, then sign in with those exact
credentials from US1; confirm no sign-up page/endpoint exists anywhere in the app.

- [ ] T030 [US2] Implement `frontend/scripts/create-user.ts` per `contracts/create-user-cli.md`: reads `DATABASE_URL_UNPOOLED` (exits non-zero with a clear message if unset), takes `<username> <password>` argv (usage message + non-zero exit if fewer than 2), lowercases the username, hashes the password with `bcryptjs`, inserts into `users`, prints the new `id` and `username` only (never the hash/password) on success, exits non-zero with "username already exists" on a unique-constraint violation without touching the existing row.
- [ ] T031 [P] [US2] Write `frontend/test/scripts/create-user.test.ts` (against a test DB or a mocked `pg` client): happy path inserts and prints id+username; duplicate username fails without modifying the existing row; missing `DATABASE_URL_UNPOOLED` fails fast; missing args prints usage.
- [ ] T032 [US2] Confirm (via `grep`/review, not a new file) that no route or page under `frontend/src/app` exposes account creation — add this as an explicit check in `quickstart.md`'s existing verification steps if not already implied.

**Checkpoint**: US1 + US2 together are a complete, demoable login flow — an account can be
provisioned and used end to end locally.

---

## Phase 5: User Story 3 - The system stops a user who sends too much, too fast, or too expensively (Priority: P1)

**Goal**: per-account rate limit (20/min) and daily token budget (200k/day) enforced before the
agent runs, with the exact existing `#4` contract error shapes.

**Independent Test**: script >20 requests/minute from one account — some get `429 rate_limited`
with `retryAfterSeconds`; simulate a day's usage at/above 200,000 tokens — the next request gets
`429 budget_exhausted`; a second account is unaffected by the first's limits; a turn already
streaming finishes even if a limit is hit meanwhile.

- [ ] T033 [P] [US3] Create `backend/app/limits/store.py`: `increment_rate(conn, user_id) -> int` (upsert `rate_limit_minute` keyed by `(user_id, date_trunc('minute', now()))`, `ON CONFLICT DO UPDATE SET request_count = request_count + 1 RETURNING request_count`, opportunistically deleting rows with `window_start < now() - interval '2 minutes'` in the same statement/transaction); `get_daily_usage(conn, user_id, usage_date) -> int`; `add_daily_usage(conn, user_id, usage_date, tokens) -> None` (upsert, add to existing `tokens_used`).
- [ ] T034 [US3] Create `backend/app/limits/enforce.py`: `check_rate_limit(conn, user_id, limit) -> Reservation` (calls `increment_rate`, `allowed = count <= limit`, on refusal computes `retryAfterSeconds` = seconds to the next minute boundary); `current_local_date(tz_name) -> date` using `zoneinfo.ZoneInfo(tz_name)` (R6); `check_budget(conn, user_id, budget, tz_name) -> Reservation` (on refusal, `retryAfterSeconds` = seconds to next local midnight); `record_usage(conn, user_id, prompt_tokens, completion_tokens, tz_name) -> None`.
- [ ] T035 [P] [US3] Write `backend/tests/limits/test_enforce.py` with a fake/injectable clock: 20 requests in a minute succeed, the 21st is refused with the right `retryAfterSeconds`; a new minute resets the count; a budget at/over 200000 refuses with `retryAfterSeconds` to the next `America/Campo_Grande` midnight; exactly at midnight the budget is available again; two different `user_id`s never affect each other's counters.
- [ ] T036 [US3] Edit `backend/app/api/chat.py`: after `require_service_account` succeeds and before the agent graph runs, call `check_rate_limit` then (if that passed) `check_budget`; on refusal return the exact `429` body/`Retry-After` header from `contracts/rate-limit-and-budget.md` (`rate_limited` checked first, cheaper and more common per that contract's "independent of each other" note); after the turn finishes (success or client-dropped-stream, but not if no model call happened), call `record_usage` with the turn's actual prompt/completion token counts.
- [ ] T037 [P] [US3] Write `backend/tests/api/test_chat_auth_and_limits.py`: request without a token → 401; valid token, under limits → proceeds to the (fake) agent; 21st request in a minute → 429 `rate_limited` with `Retry-After`; budget exhausted → 429 `budget_exhausted`; a turn already in progress when a limit is hit completes and streams its full answer, only the *next* request is refused (FR-013).
- [ ] T038 [US3] Add the two 429 fixtures already referenced (`http-429-rate-limited.json`, `http-429-budget-exhausted.json` under `contracts/chat-stream/fixtures/`) to any contract-test harness that validates real backend output against `docs/contracts/chat-stream.md` fixtures, if such a harness exists for other error cases (check `backend/tests/` for the existing `http-401.json` contract test and mirror its pattern).

**Checkpoint**: US1 + US2 + US3 — a provisioned account can log in, chat, and gets stopped cleanly
once it exceeds rate or budget; another account is unaffected.

---

## Phase 6: User Story 4 - A conversation belongs to the person who is signed in (Priority: P1)

**Goal**: close the DL-012 residual risk — a conversation id alone never grants access to another
account's verified order data. (Schema/state-layer work for this was front-loaded into the
Foundational phase — T008, T009, T014 — because every other story's tests run against the
account-scoped state; this phase is the story-level acceptance test and any remaining wiring.)

**Independent Test**: sign in as account A, verify an order in conversation C; sign in as account
B, send a message with conversation id C; B must be asked to verify again and must not see A's
order.

- [ ] T039 [US4] Write `backend/tests/api/test_chat_conversation_scoping.py`: full request-level test (through `POST /api/chat`, using two distinct valid service JWTs for two different `user_id`s and the same `conversation_id`) proving account B's request never reads account A's `verified_order_ids` (SC-007); this is the end-to-end complement to the unit-level `test_state_scoping.py` from T014.
- [ ] T040 [US4] Audit `backend/app/tools/` (and any other module importing `app.agent.state`) for a call that still passes only `conversation_id` without a `user_id`, following the signature change from T009; fix any found (should be none if T015 was thorough — this is a verification task, not expected to add new code).

**Checkpoint**: all four P1 stories done — this is the realistic "safe to deploy publicly" MVP per
constitution V.

---

## Phase 7: User Story 5 - The production deployment fails safe, not open (Priority: P2)

**Goal**: missing/invalid required production config stops traffic instead of silently running
open.

**Independent Test**: start the backend in `Environment.PRODUCTION` with `service_jwt_secret`
unset — it must not serve chat requests.

- [ ] T041 [US5] Add a startup check in `backend/app/main.py` (app construction / lifespan): if `settings.environment is Environment.PRODUCTION`, raise `RuntimeError` listing which of `service_jwt_secret`, `database_url`, and the configured LLM provider's key are missing/empty — fail loudly rather than start half-configured (R7, FR-015).
- [ ] T042 [P] [US5] Write `backend/tests/test_fail_closed_startup.py`: constructing the app with `environment=production` and a missing `service_jwt_secret` (or `database_url`) raises; with all required values present, it does not raise.
- [ ] T043 [US5] Confirm (by inspection, documented as a one-line note in `research.md` R7 if anything changes) that `require_service_account` (T011) independently treats a falsy `service_jwt_secret` as a 500 even if the startup check in T041 were ever bypassed — defense in depth already implemented in Phase 2; no new code expected here.

**Checkpoint**: a misconfigured production deploy fails fast and loud instead of serving traffic.

---

## Phase 8: Polish & Production Deploy

**Purpose**: cross-cutting cleanup and the user-executed production rollout (quickstart.md).

- [ ] T044 [P] Run `cd backend && uv run ruff check . && uv run pytest` and fix any lint/type issues introduced by T001–T043.
- [ ] T045 [P] Run `cd frontend && pnpm lint && pnpm typecheck && pnpm test` and fix any issues introduced by T001–T043.
- [ ] T046 Update `docs/contracts/chat-stream.md` if any detail of the 401/429 responses implemented differs from what is already documented there (it should not, per contracts/*.md in this feature — this is a consistency check, not expected to require changes).
- [ ] T047 Append a `DL-DOCS-xxx` (spec/plan) and, once implemented, `DL-BE-xxx`/`DL-FE-xxx` entries to `docs/decision-log.md` per `CLAUDE.md`'s numbering rule, summarizing the auth/limits/fail-closed design and the DL-012 residual-risk closure.
- [ ] T048 Update `docs/HANDOFF.md` Status and Session log per the `living-handoff` convention once this feature is implemented and reviewed.
- [ ] T049 (User-executed, not by an agent without explicit go-ahead) Follow `quickstart.md`'s "Production deploy" section: set `SERVICE_JWT_SECRET`/`AUTH_SECRET` in Vercel, let the new tables/schema apply on first production request, run `create-user` against `DATABASE_URL_UNPOOLED`, set the OpenRouter workspace spend cap, redeploy, and run the end-to-end production verification (FR-017, SC-006).

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)**: strictly sequential; Foundational blocks every
  user story (the service-JWT dependency and account-scoped state are shared by all of them).
- **US1 (Phase 3)**: depends only on Foundational. Can be demoed with a manually-inserted `users`
  row before US2 exists (T029 flags this).
- **US2 (Phase 4)**: depends only on Foundational + the `users` table (T005); independent of US1's
  frontend work except that testing it end-to-end wants US1's login form. Could be built in
  parallel with US1 by a second contributor.
- **US3 (Phase 5)**: depends on Foundational (T011's `require_service_account`, T015's wiring point
  in `chat.py`) and on US1 existing enough to generate a real service JWT for manual testing, but
  its own backend code (T033–T038) has no code dependency on US1/US2 and can be built in parallel.
- **US4 (Phase 6)**: its implementation is mostly already done by Foundational (T008/T009); this
  phase is verification. Depends on Foundational only.
- **US5 (Phase 7)**: independent of US1–US4's code; can be done any time after Setup.
- **Polish (Phase 8)**: after all stories are implemented and reviewed.

## Parallel Execution Examples

- Within Foundational: T005 and T006 (different schema files) in parallel; T012, T013, T014 (three
  different test files, all read-only against already-written T010/T011/T009) in parallel once
  their respective implementation tasks land.
- Across stories once Foundational is done: one contributor on US1 (T016–T029), another on US3's
  backend half (T033–T038), another on US5 (T041–T043) — none of these touch the same files except
  all eventually touching `backend/app/api/chat.py` (T015, T025 forwarding, T036), so that file's
  edits should land as small, sequential commits even if designed in parallel.

## Implementation Strategy

**MVP = Phases 1–6 (Setup, Foundational, US1–US4)**: this is the smallest safe-to-deploy-publicly
slice per constitution V — login without limits, or limits without the conversation-ownership fix,
both leave a real exposure documented in this spec/DL-012. US5 (Phase 7) and the production
rollout (Phase 8) follow immediately after, since the brief's deadline leaves no room for a
second iteration.

Suggested PR split (small PRs per working agreement):
1. Foundational (Phase 2) — schema + service-JWT verify + conversation scoping.
2. US1 (Phase 3) + US2 (Phase 4) — login end to end, including the CLI.
3. US3 (Phase 5) + US4 (Phase 6 verification) — limits and the DL-012 closure test.
4. US5 (Phase 7) — fail-closed startup check.
5. Docs/handoff update + (user-run) production deploy — Phase 8.
