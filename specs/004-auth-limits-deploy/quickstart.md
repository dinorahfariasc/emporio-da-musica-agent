# Quickstart: validate 004 end-to-end

## Local

1. `docker compose up -d --wait` (Postgres already used by the rest of the project).
2. The new tables (`users`, `login_attempts`, `rate_limit_minute`, `token_usage_daily`) and the
   `conversation_state` schema change are applied idempotently on first backend request, same as
   the existing agent tables — no manual step needed locally; `uv run pytest` and `uv run uvicorn`
   both trigger it.
3. Set `SERVICE_JWT_SECRET` to the same arbitrary string in both `backend/.env` and
   `frontend/.env.local`; set `AUTH_SECRET` (Auth.js) in `frontend/.env.local` (any random string
   locally, e.g. `openssl rand -base64 32`).
4. Create a local test account:
   `cd frontend && DATABASE_URL_UNPOOLED=$DATABASE_URL CREATE_USER_PASSWORD=a-fine-long-password pnpm tsx scripts/create-user.ts demo`
5. `cd backend && uv run pytest` — unit tests for JWT verify, rate limit, budget, fail-closed
   startup check should pass with no network access.
6. `cd frontend && pnpm dev`, open `http://localhost:3000` → redirected to `/login` → sign in with
   `demo` / `demo-password` → reach the chat and get a real answer (`CHAT_MODE=backend` needed, per
   the existing frontend `.env.example`).
7. Exercise the rate limit: script 25 requests in under a minute from the same session; confirm
   some return 429 with the `rate_limited` body from `contracts/rate-limit-and-budget.md`.
8. Exercise the budget: temporarily set `daily_token_budget` low (e.g. 50) via an env var override
   for a local run, send one message, confirm the next is refused with `budget_exhausted`; reset
   and confirm it recovers after changing `usage_date` forward (fake clock in the test, not real
   waiting) — this scenario should primarily be covered by the `pytest` fake-clock tests, not
   manual testing.
9. Fail-closed check: unset `SERVICE_JWT_SECRET` on the backend only, restart it, confirm
   `/api/chat` now fails every request (500, not silently open) and confirm `/api/health` can still
   report what's wrong without leaking the secret's value.
10. Conversation-scoping check (FR-009a, SC-007): create a second local account
    (`CREATE_USER_PASSWORD=another-long-password pnpm tsx scripts/create-user.ts demo2`), verify an order in a conversation as
    `demo`, then send a message with that same conversation id signed in as `demo2`; confirm `demo2`
    is asked to verify again and never sees `demo`'s verified order.
11. Lockout check: submit the wrong password for `demo` 6 times within a minute; confirm the 6th
    (and any further attempt within 15 minutes) is refused even with the correct password.

## Production deploy (user-run; agent prepares, never executes against prod per working agreements)

1. Set `ENVIRONMENT=production` on the backend Service explicitly (belt-and-suspenders: Vercel's
   own `VERCEL_ENV=production`, set automatically, is also checked, so forgetting this does not
   fail open — but it is still the documented, intended value). Add `SERVICE_JWT_SECRET` (new,
   shared, **at least 32 random characters** — a shorter value is rejected at request time in
   production) and `AUTH_SECRET` (new, Auth.js) to the Vercel project's environment variables, for
   both the `frontend` and `backend` Services as applicable (`SERVICE_JWT_SECRET` on both;
   `AUTH_SECRET` on `frontend` only; `ENVIRONMENT` on `backend` only).
2. The new/changed tables apply themselves idempotently on first request against production too
   (same advisory-locked DDL pattern as the existing agent tables, DL-012); no manual DDL step is
   required, but the first production request after deploy will pay that one-time cost. A
   `conversation_state` table from before this feature (no `user_id` column) is detected and
   migrated in place automatically (dropped and recreated under the same advisory lock — it only
   ever held ephemeral per-turn verification state, nothing a customer would notice missing).
3. Run the `create-user` CLI against production (`DATABASE_URL_UNPOOLED` from Vercel's env, not
   committed anywhere) to provision the reviewer account(s); record the username(s) somewhere the
   user will share out of band with the reviewer — never in the repo.
4. Set an organization/workspace spend limit in the OpenRouter dashboard (current LLM provider per
   DL-012) as a backstop behind the per-user daily budget (FR-016); record the configured amount in
   `docs/decision-log.md` (DL-DOCS-xxx), not the key itself.
5. Redeploy both Vercel Services so the new env vars take effect (env changes only reach
   deployments created afterwards, per HANDOFF §5).
6. End-to-end verification (FR-017, SC-006): from a browser with no prior session, open the
   production URL, confirm redirect to `/login`, sign in with a real provisioned account, send a
   message and get a real answer, then script >20 requests/min against the production URL with
   that account's session to confirm a 429 appears (do this gently — it is hitting the real
   deployment and the real provider spend for a few turns).
7. Update `docs/HANDOFF.md` Status and append the decision-log entries for: the models/limits
   chosen here (if any changed from the spec defaults), the spend-cap amount configured, and the
   date production verification was done.
