# Phase 1 Data Model: Auth, limits, cost controls and production deploy

All new tables live in the existing Neon Postgres database and are created the same way
`conversation_state` already is (`backend/app/agent/schema.sql`): idempotent
`CREATE TABLE IF NOT EXISTS` SQL, applied lazily on first use via an `ensure_*_tables()` helper
and once at the end of the seed. `users` and `login_attempts` live in `backend/app/auth/schema.sql`;
`rate_limit_minute` and `token_usage_daily` live in `backend/app/limits/schema.sql`. No separate
numbered-migrations mechanism is introduced (see `quickstart.md`).

## `users`

Reviewer login accounts. Created only by the `create-user` CLI (FR-004); no code path inserts a
row from a request.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` (default `gen_random_uuid()`) | Primary key; this is the `sub` claim in the service JWT. |
| `username` | `text`, unique, not null | Case-sensitive; lowercase enforced by the CLI before insert. |
| `password_hash` | `text`, not null | bcrypt hash (via `bcryptjs`); never logged, never returned by any query used outside the login path. |
| `created_at` | `timestamptz`, default `now()` | |
| `disabled_at` | `timestamptz`, nullable | Set instead of deleting, so a disabled account's historical usage rows stay attributable; `authorize()` rejects login when set (Edge case: account disabled after login must stop working on the *next* request — enforced because the service JWT is short-lived, so a disabled account's session JWT still works but the next-minted service JWT's verification step re-checks `disabled_at` is null before forwarding... see note below). |

**Note on the "disabled after login" edge case**: the Auth.js session JWT itself is not re-checked
against the DB on every page view (that is Auth.js's normal JWT-session behavior). The spec's
requirement is satisfied at the layer that matters — the BFF route handler re-reads `disabled_at`
from `users` each time it mints a service JWT for a chat request (it already needs a DB round trip
for nothing else here, but the account is looked up once at login and the disabled check is cheap
to repeat), so a disabled account stops being able to *chat* immediately, even if its browser
session cookie is still technically valid. Full immediate sign-out on disable is out of scope.

## `rate_limit_minute`

Per-account request counter for the current UTC minute. One row is created/updated per request
that reaches the limit-check step (i.e., after the service JWT verifies, before the agent runs).

| Column | Type | Notes |
|---|---|---|
| `user_id` | `uuid`, references `users(id)` | |
| `window_start` | `timestamptz`, not null | `now()` truncated to the minute (`date_trunc('minute', now())`), UTC. |
| `request_count` | `int`, not null, default 0 | Incremented atomically by the enforcing query. |
| | | **Primary key**: `(user_id, window_start)`. |

Old rows are harmless (one row per account per minute that had traffic) but are opportunistically
deleted for rows older than 2 minutes as part of the same upsert transaction, to keep the table
small — no separate cleanup job needed at this scale.

## `token_usage_daily`

Per-account cumulative token usage for a given local day.

| Column | Type | Notes |
|---|---|---|
| `user_id` | `uuid`, references `users(id)` | |
| `usage_date` | `date`, not null | The request's "now" converted to `America/Campo_Grande`, truncated to a date (R6). |
| `tokens_used` | `int`, not null, default 0 | Sum of prompt+completion tokens from every turn that ran that day; updated once per finished turn (not per streamed chunk). |
| | | **Primary key**: `(user_id, usage_date)`. |

A turn that fails before producing a model response does not add tokens (nothing was spent); a
turn that fails partway through after already calling the LLM records whatever usage the provider
response reports, same as the existing router/model telemetry already logs today.

## `login_attempts`

Backs the sign-in lockout (FR-005). One row per username; reset on a successful login.

| Column | Type | Notes |
|---|---|---|
| `username` | `text`, primary key | Not a foreign key to `users` — a lockout must also work against a username that does not exist, so a guesser cannot distinguish "wrong password" from "no such account" by timing or by this table's absence. |
| `failed_count` | `int`, not null, default 0 | Incremented on each failed attempt within the current window. |
| `window_start` | `timestamptz`, not null | Reset (row deleted or `failed_count` zeroed) when a login succeeds, or when `now() - window_start > 15 minutes`. |

## Conversation scoping (a column added to an existing table, not a new one)

`conversation_state` (added in `002-agent-core`, `backend/app/agent/schema.sql`) is keyed only by
`conversation_id` today — exactly the DL-012 residual risk this feature closes. This feature adds
a `user_id` column to `conversation_state`, changes its primary key to `(user_id, conversation_id)`,
and changes every read/write in `app/agent/state.py` (`get`, `reserve_attempt`, and the verify/lock
functions alongside them) to take the account id from the verified service JWT, not just the
client-supplied conversation id. A migration backfills existing rows as orphaned (no safe owner to
assign; this table only ever held pre-production/eval data) or simply drops and recreates the table,
since no real production conversations exist yet. See FR-009a and `research.md` R10.

## Service JWT claims (not a table — the in-flight credential, R4)

| Claim | Meaning |
|---|---|
| `sub` | `users.id` (uuid, as a string) |
| `username` | for logging/telemetry only, never trusted for authorization decisions |
| `iat` / `exp` | issued-at / expiry; `exp - iat` = 60 seconds |

FastAPI's `require_service_account` dependency (`app/auth/dependency.py`) verifies signature and
`exp`, then returns an `AccountClaims(user_id, username)` used as the key for both limit tables.
It never looks anything up in `users` itself — the BFF already did the disabled-account check at
mint time (see note above); the backend only needs an opaque, trusted account id to key the
counters.
