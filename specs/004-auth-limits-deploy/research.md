# Phase 0 Research: Auth, limits, cost controls and production deploy

## R1 — Auth.js version and session strategy

**Decision**: `next-auth@5` (Auth.js), Credentials provider, **JWT session strategy** (not
database sessions).

**Rationale**: a database session strategy needs the full Auth.js adapter schema (`sessions`,
`verificationTokens`, etc.) for a feature that only ever needs one provider and no OAuth linking.
JWT sessions need only the app's own `users` table, checked inside `authorize()`. Auth.js v5 is
the version with first-class Next.js App Router middleware support (`auth()` export usable in
`src/proxy.ts` — Next.js 16 renamed "middleware" to "proxy"; with a `src/` layout the file must
live at `src/proxy.ts`, next to `app/`, not at the project root, or it is silently never loaded),
matching Next 16 already in use.

**Alternatives considered**:
- Roll a custom cookie/session system — rejected: reimplements CSRF-safe cookies, signing and
  expiry that Auth.js already provides correctly; higher risk for a same-day deadline.
- Database session strategy — rejected: unnecessary tables/adapter code for one credentials
  provider and a handful of accounts.

## R2 — Password hashing library

**Decision**: `bcryptjs` (pure JavaScript implementation) on both the Next.js login path and the
`create-user` CLI.

**Rationale**: Vercel Functions support native addons, but `bcrypt` (the native binding) has
caused cold-start/bundle friction on serverless platforms before (wrong prebuilt binary for the
function's architecture). `bcryptjs` has no native step, is small, and is fast enough for a
handful of accounts with normal login-rate traffic.

**Alternatives considered**:
- `bcrypt` (native) — rejected: native build risk documented project-wide as a Vercel gotcha class
  (HANDOFF §6 already flags "no native/compiled dependency" risk for the bundle).
- Node's built-in `crypto.scrypt` — viable but more code to get right (salt generation/encoding,
  timing-safe compare) for no benefit over a maintained, audited library.

## R3 — Where the password check and the `users` table live

**Decision**: the `users` table lives in the same Neon Postgres database as everything else
(`DATABASE_URL`). The Next.js `authorize()` callback and the `create-user` CLI talk to it with a
minimal `pg` client (new frontend dependency); no ORM.

**Rationale**: constitution VI (no dependency without a present need) and the project pattern
(backend already talks to the same Postgres directly via `psycopg`, no ORM there either). A
second database would add an operational moving part for one small table.

**Alternatives considered**:
- Auth.js email/passwordless magic links — rejected: needs an email provider (SES/Resend) that is
  out of scope and unnecessary for an internal reviewer login (spec explicitly: no self-service,
  credentials handed out of band).
- Storing users in an environment variable (static allow-list) — rejected: fails FR-004 (a CLI
  that *creates* an account) and makes rotating/adding an reviewer require a redeploy.

## R4 — Service-to-service trust (BFF → FastAPI)

**Decision**: the Next.js route handler for `/api/chat` mints a short-lived (60s) HS256 JWT after
confirming the Auth.js session, with claims `sub` (username), `iat`, `exp`, signed with
`SERVICE_JWT_SECRET` (a value shared between the two Vercel Services, set as an env var on both).
FastAPI verifies signature + expiry with `PyJWT` before accepting the request. Minted with `jose`
on the Node side (already the modern standard for Auth.js-adjacent JWT work, no native deps).

**Rationale**: matches the decision already recorded in `docs/decision-log.md` DL-011/012 context
and `docs/planning/backlog.md` E5 ("Next.js route handler acts as a BFF and calls FastAPI with a
short-lived HS256 service JWT"); FastAPI never sees a password (constitution V) and the credential
has a tiny blast radius if logged or leaked (60s).

**Alternatives considered**:
- Passing the raw Auth.js session cookie/JWT straight through to FastAPI — rejected: couples the
  backend to Auth.js's own JWT format/rotation and widens what a backend-side bug could expose;
  the BFF boundary should own translating "user is logged in" into "this specific request is
  authorized".
- A long-lived or non-expiring service API key per user — rejected: defeats "short-lived" (spec
  FR-009) and the point of binding the token to the specific request's account.

## R5 — Rate limit and daily budget storage

**Decision**: two small Postgres tables, both keyed by `user_id`:
- `rate_limit_minute(user_id, window_start timestamptz, request_count int)` — `window_start` is
  the current UTC timestamp truncated to the minute; enforced with `INSERT ... ON CONFLICT
  (user_id, window_start) DO UPDATE SET request_count = request_count + 1 RETURNING
  request_count`, refuse if the returned count exceeds 20.
- `token_usage_daily(user_id, usage_date date, tokens_used int)` — `usage_date` is "now" converted
  to `America/Campo_Grande` and truncated to a date; checked before the turn starts (refuse if
  `tokens_used >= 200000`) and incremented by the turn's actual prompt+completion tokens after it
  finishes.

**Rationale**: constitution VI/YAGNI — a single-digit number of accounts does not need Redis or a
distributed limiter; Postgres row-level atomic upsert is enough and keeps one less moving part in
a same-day deploy. Fixed-window (not sliding-window/token-bucket) rate limiting is a known,
accepted simplification (a client could in theory send ~2x the limit across a window boundary);
documented here rather than engineered away, since the realistic adversary at this scale is a
runaway client/bug, not a sophisticated rate-limit evader.

**Alternatives considered**:
- Upstash/Redis rate limiting — rejected: another managed service and env var to wire up and
  fail-close correctly, for a one-reviewer deployment; Postgres is already a hard dependency.
- Sliding-window log (store every request timestamp) — rejected: more rows and query complexity
  for a limit this small; the fixed-window edge case is an accepted, documented trade-off.

## R6 — Day boundary computation

**Decision**: compute "today" in `America/Campo_Grande` in Python using the standard library
`zoneinfo` (`datetime.now(ZoneInfo("America/Campo_Grande")).date()`), not a Postgres session
timezone setting.

**Rationale**: keeps the timezone rule visible and testable in application code (fake-clock unit
tests per constitution IV) rather than relying on a database/connection-pool setting that could
silently differ between local dev and Neon.

## R7 — Fail-closed production config

**Decision**: extend `app/config.py`'s `Settings` with the new required-in-production fields
(`service_jwt_secret`, and the existing `database_url`/LLM provider key already covered). Add a
single startup check — run once when the FastAPI app is constructed (`app/main.py`) — that raises
`RuntimeError` if `environment == Environment.PRODUCTION` and any of `service_jwt_secret`,
`database_url`, or the configured LLM provider's key is missing/empty. A crashed/never-healthy
function fails every request closed (Vercel will show 500s, not silently serve traffic).
Additionally, the JWT-verification dependency itself treats an empty/unset secret as a
configuration error (500), never as "accept any token" — defense in depth independent of the
startup check.

**Rationale**: spec FR-015 explicitly requires refuse-to-start-or-refuse-requests, not a default
that could be insecure. Two independent checks (startup + per-request) mean a future change that
weakens one doesn't silently reopen the hole.

**Alternatives considered**:
- Only a per-request check — rejected: a slow leak (e.g. a different code path constructing the
  verifier without going through settings) could miss it; startup-time is the stronger guarantee
  for the bundle generally.

## R8 — Session lifetime and login UX

**Decision**: Auth.js JWT session max age: 30 days (Auth.js default order of magnitude), sliding
on activity (Auth.js's default `updateAge` behavior). Login form: username + password, generic
error message on any failure ("invalid username or password"), redirect back to the originally
requested page (`callbackUrl`) after success — reusing the existing `LoginNotice` component's
`reason=expired` query-param convention already present in the placeholder.

**Rationale**: spec Assumptions call this an implementation detail within "a standard multi-day
session"; 30 days matches an reviewer's realistic review window without requiring re-login mid
evaluation, while still expiring eventually rather than being eternal.

## R10 — Closing the conversation-id residual risk (DL-012)

**Decision**: add `user_id` to the existing `conversation_state` table (`002-agent-core`,
`backend/app/agent/schema.sql`) and change its primary key from `(conversation_id)` to
`(user_id, conversation_id)`. Every function in `app/agent/state.py` that reads or writes
conversation state now takes the account id from `require_service_account`'s verified claims, not
only the conversation id the client sends.

**Rationale**: `docs/decision-log.md` DL-012 already documents this exact gap as a known,
accepted-for-now risk ("until #10 binds the chat id to a user, anyone who knows a chat id sees the
orders verified in it"). This feature is "#10", so closing it here — rather than leaving it for a
later feature — is both in scope and the reason DL-012 gave for deferring it in the first place.
Folded in from a parallel spec draft (`docs/10-auth-limits-spec`) that called this out explicitly
as User Story 3/4; it was missing from this plan's first pass and is a real security requirement,
not a nice-to-have.

**Alternatives considered**:
- Leaving conversation state keyed by conversation id alone and relying on conversation ids being
  hard to guess (they already match `^[A-Za-z0-9_-]{1,128}$`, client-generated) — rejected: "hard
  to guess" is not "requires authorization", and DL-012 already flagged this as unacceptable once
  the system is public.
- A separate mapping table (`conversation_owners`) instead of widening the primary key — rejected:
  more moving parts for the same guarantee; widening the key makes an unscoped read impossible to
  write by accident (the query needs both values or it does not compile against the new schema).

## R11 — Sign-in lockout

**Decision**: a `login_attempts` table (keyed by username, not by IP) backs a 5-attempts-per-
15-minutes lockout, checked by the Auth.js `authorize()` callback before (not instead of) the
password comparison.

**Rationale**: folded in from the parallel spec draft; a handful of credentials sitting behind a
public login form on the internet will see automated credential-stuffing attempts regardless of
how few real users exist, and the cost of adding this is one small table and one check.

**Alternatives considered**:
- IP-based lockout — rejected: more complex (proxies, shared/dynamic IPs for a legitimate
  reviewer) for a project this size; username-based is simpler and matches the actual threat
  (guessing one reviewer's password), accepting the trade-off that it cannot stop a
  distributed attacker from trying many *different* usernames.
- No lockout at all — rejected now that a specific, cheap mitigation was already specified by a
  parallel review of the same issue; declining it without a stated reason would be worse than
  adopting it.

## R12 — Anthropic/OpenRouter workspace spend limit

**Decision**: out of code scope (spec FR-016 asks only that it be configured and documented).
Plan: document in `quickstart.md`/README that the user sets a workspace/organization-level spend
cap in the OpenRouter dashboard (the project's current LLM provider per DL-012) as a backstop
behind the per-user daily token budget enforced in this feature.

**Rationale**: constitution's "facts/limits computed in Python" is about user-facing eligibility
logic; a provider billing cap is an operational safety net outside the application, consistent
with how the rest of the project treats provider dashboards (API keys, models) as user-held
configuration, not code.
