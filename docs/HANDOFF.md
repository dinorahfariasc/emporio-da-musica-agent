# Handoff — how to continue this project with any AI agent

Read this first, then `CLAUDE.md` (rules), `.specify/memory/constitution.md` (principles) and
`docs/decision-log.md` (why things are the way they are). This file is the **current state**;
update it at the end of every work session.

_Last updated: 2026-11-01 (#6 agent core merged as #40; #7 actions re-opened against main)._

## 1. What this is

Artefact AI Engineer take-home: a customer-service agent ("Melody") for a fictional music store,
**Empório da Música**. Brief: `challenge/challenge_brief.pdf`. Data: `challenge/data/`.
Deliverables: public repo with real commit history, README (run instructions, decisions,
limitations, **AI-assistant workflow**), 3–5 example conversations. **Deadline: P0 done by
2026-11-01 evening (America/Campo_Grande); D2 (11-02) is improvements only. The brief forbids any
change to the repo after the delivery time (exact time: ask the user, it is in their email).**
The repo is private now; the user makes it public at delivery.

## 2. Where everything lives

| What | Where |
|---|---|
| Source of truth for scope | GitHub issues #2–#23 + board https://github.com/users/dinorahfariasc/projects/4 |
| Epic ↔ spec mapping | `docs/planning/backlog.md` (has the issue-number table) |
| Specs (Spec Kit) | `specs/NNN-*/` (spec → plan → tasks) |
| Decisions and AI usage | `docs/decision-log.md` (append an entry for every decision) |
| Chat API contract | `docs/contracts/chat-stream.md` + `contracts/chat-stream/fixtures/` |
| Data rules / anomalies | `docs/data-quality-report.md`, `specs/001-data-foundation/data-model.md` |
| Backend | `backend/` — FastAPI, flat `app/` package, `etl/`, uv, Python 3.13 |
| Frontend | `frontend/` — Next.js 16 (Cache Components), ai@7, @ai-sdk/react@4, pnpm |
| Deploy | `vercel.json` (Vercel Services: public `frontend`, private `backend`) |
| Production URL | https://emporio-da-musica-agent.vercel.app |

## 3. Status (update me)

**Merged to `main`:** #2 bootstrap · #3 scaffolding + walking skeleton · #4 chat stream contract ·
embeddings switch to Gemini · #5 store ETL, retrieval (#35) · #36/#38 chat web (US1, mobile) · #39
agent-core plan · **#40 agent core (PR 1 of 002)**: router, `create_agent`, stream adapter,
`POST /api/chat`, 8 read tools, 20 fake scenarios, OpenRouter provider, review fixes (DL-012).

**In flight (check `gh pr list` and the board for the truth):**
- **#7 actions (PR 2 of 002)**: return eligibility, `check_return_eligibility`, `request_return`,
  `register_complaint`, `handoff_to_human`, US6 scenarios, UI label (DL-013). #41 was merged into
  the stale `feat/6-agent-core` branch after #40 was squashed, so it never reached `main`; the same
  commit is re-opened from `feat/7-actions-main`. Needs the user's merge.
- **Models (DL-012):** router `perplexity/pplx-decider-v1.2`, specialist `openai/gpt-6-luna`, general
  `deepseek/deepseek-v4.1-flash`, all through OpenRouter. Production env: `CHAT_MODE=backend`,
  `LLM_PROVIDER=openrouter`, `ROUTER_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, `ROUTER_MODEL`,
  `SPECIALIST_MODEL`, `GENERAL_MODEL`, `GEMINI_API_KEY`, `EMBEDDINGS_PROVIDER=gemini`; the user
  runs the redeploy.
- **#5 T032:** manual seed of Neon with Gemini (user holds the keys) is still pending; local seeds use
  the fake embedder, and the seed and the query must use the same provider.
- **Not started:** #8 MCP (PR 3 of 002, T034–T036), #10 auth/limits/deploy, #11 README + example
  conversations. Open nits from the #40 review are in DL-012 (stream close on error, body size cap).

**Remaining P0 order:** merge #7 → #8 MCP → #10 → #11 (README, example conversations; run `python -m evals --live --export docs/conversations/`). Do P1/P2 only after
all P0 is in production.

## 4. Working agreements (from the user)

- **Spec-Driven:** no implementation without spec + plan + tasks for the epic (Spec Kit skills in
  `.claude/skills/speckit-*`; scripts in `.specify/`). Feature numbers are fixed:
  001 data, 002 agent, 003 chat web, 004 auth/limits/deploy, 005 admin dashboard.
- **Review gate:** every spec PR and every code PR is reviewed by **two reviewers** — one QA, one
  senior engineer — before the user merges. Post a consolidated review comment on the PR.
- **Commits/PRs:** English, semantic (`feat:` `fix:` `docs:` `test:` `chore:`), small, `Closes #n`
  / `Part of #n`. **Never mention AI/Claude in commits or PRs and never add `Co-Authored-By`
  trailers** — even if a tool's default asks for it. AI usage is documented in the decision log
  and README instead. The **user merges** PRs; agents open them.
- **Language:** everything English except the agent persona and the website copy (pt-BR first).
- **Decision log numbering:** next free is DL-014 (check the file; parallel branches collide).
- **Facts from the system:** prices, stock, promos, eligibility are computed in Python, never by
  the LLM (constitution I).
- Update the board status and this file as you go.

## 5. Environment

| Item | Notes |
|---|---|
| Local DB | `docker compose up -d --wait` → Postgres 16 + pgvector on **localhost:5433** (override with `POSTGRES_PORT`; another project may hold 5432/5433) |
| Backend | `cd backend && cp .env.example .env && uv sync && uv run pytest` — no keys needed (fake providers by default). Real models: set the `*_PROVIDER=openrouter` vars and `OPENROUTER_API_KEY`; `uv run python -m evals --live` and `uv run python -m evals.router_spike <model ids>` |
| Frontend | `cd frontend && cp .env.example .env.local && pnpm install && pnpm dev` (`CHAT_MODE=mock` replays fixtures; **production must use `backend`**) |
| Secrets (never commit) | `GEMINI_API_KEY` (embeddings, free tier), `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY`, `TYPESAFE_API_KEY` (Jev router). Production values live in Vercel env vars; the user holds the keys. |
| Neon (prod DB) | Vercel Marketplace integration; vars `DATABASE_URL` (pooled) and `DATABASE_URL_UNPOOLED` (use for seed/DDL). Region São Paulo; Vercel functions run in `iad1` (latency follow-up: move to `gru1`). |
| Vercel | Single project `emporio-da-musica-agent`; env changes only reach deployments created afterwards (redeploy). Production redeploys must be run by the user. |
| CLI auth | `gh` is logged in as `dinorahfariasc` (scopes include `project`); `npx vercel login` done on the user's machine. |

## 6. Gotchas learned the hard way

- **Versions are newer than most docs:** ai@7 (not v5), Next 16 with Cache Components (no
  `export const dynamic`; use `await connection()`), Vitest 5. Check `node_modules` types and
  `node_modules/next/dist/docs` before using an API.
- `.env*` ignore rules hide `.env.example`; keep the explicit `!.env.example`.
- CSV files use CRLF line endings; never rewrite them (`challenge/** -text`).
- A PR whose base is another PR's branch merges into that branch, not into `main` (#41 did). Retarget to `main` before merging, or cherry-pick onto `main` afterwards.
- Live evals: one event loop (`evals/runner.py::_live_client`); decider models are not chat models (`/api/alpha/decisions`); DeepSeek needs reasoning off for the router.
- Squash-merged stacked PRs conflict: retarget with
  `git rebase --onto origin/main <old-base> <branch>` then `git push --force-with-lease`.
- Vercel Services: the backend is **private**; reach it from Next.js route handlers via
  `BACKEND_URL` (binding). `/mcp` will need its own public rewrite (issue #8).
- Voyage was rejected (needs a card); embeddings are Gemini `gemini-embedding-001`, 768 dims.
- rehype-harden matches `allowedLinkPrefixes` by **origin** (needs `defaultOrigin`); `"https://"`
  blocks every link. Use `["*"]` and re-check the href in the `a` renderer.
- Streamdown renders `**bold**` as `<span data-streamdown="strong">`, not `<strong>`.
- Streamdown 2.7.1 defaults allow any image/link prefix, `data:` images and raw HTML; never use
  them as-is (see `specs/003-chat-web/research.md` R4).
- ai@7 `useChat`: a stream that closes without `finish` ends as `ready` with no error; detect it
  in `onFinish` (`!isAbort && !isError && finishReason == null`). HTTP errors arrive as
  `APICallError` (`statusCode`, `responseBody`); response headers are dropped.
- The data has deliberate anomalies (listed in the decision log DL-001 and the report); name
  beats description for products 135–144; only 4 promotions are active (90, 94, 121, 127).

## 7. Prompt to give a fresh agent

> You are continuing the Empório da Música agent project. Read `docs/HANDOFF.md`, `CLAUDE.md`,
> `.specify/memory/constitution.md` and the latest entries of `docs/decision-log.md`. Run
> `gh pr list` and look at the project board to see what is in flight. Continue with the next
> item in "Status", following the working agreements (spec-driven, two-reviewer gate, no AI
> mentions in commits, user merges). Ask the user before any production deploy, secret handling
> or merge. Update `docs/HANDOFF.md` and the decision log when you finish.

## 8. Session log (newest first)

Keep entries to 3–5 lines (Done / Fixed / Next). Condense older ones once there are ~15.

### 2026-11-01 — #40 merged; #7 re-opened against main
- **Done:** #40 merged. #41 had been merged into the stale `feat/6-agent-core` branch, so the actions commit was cherry-picked onto `main` as `feat/7-actions-main` and re-opened; HANDOFF status refreshed.
- **Next:** user merges the #7 PR; then #8 MCP, #10, #11.

### 2026-11-01 — #7 actions (PR 2 of 002)
- **Done:** returns eligibility (`app/policies/returns.py`), `check_return_eligibility`, `request_return`, `register_complaint`, `handoff_to_human`, `service_request` prompt block, US6 scenarios (fake-only with a scripted clock, plus a live-only one), UI label and contract row; 285 tests; live evals pass; DL-013. Branch `feat/7-actions` is based on `feat/6-agent-core` (#40 not merged yet).
- **Next:** user merges #40, then this PR (retarget to main); then #8 MCP (T034–T036), #10, #11.

### 2026-11-01 — Review of #40 applied
- **Done:** QA + senior review, no blockers; fixes listed in DL-012 (router fallback budget, chat id validation, history window, aclosing, DDL lock, pool timeout, store date in the prompt, PII phone, stricter live assertions). Live evals 29/29 on two runs; 248 tests.
- **Next:** user merges #40, then PR 2 of 002 (#7 actions, T030–T033). Open nits and missing scenarios are in DL-012.

### 2026-11-01 — OpenRouter provider and live evals (#6 PR 1, #40)
- **Done:** `openrouter` provider for the agent LLM and the router (`OPENROUTER_API_KEY`, `ROUTER_MODEL`); decider models go through `/api/alpha/decisions`; router spike takes model ids and passes context; live evals pass 27–29 of 29 with `openai/gpt-6-luna` (specialist) and `deepseek/deepseek-v4.1-flash` (general); see DL-012.
- **Fixed:** Jev/System One body; DeepSeek reasoning eating the router budget; eval runner event-loop reuse; prompt (greeting, Saturday hours, Portuguese policy queries).
- **Next:** push the branch, QA + senior review of #40, user merge; Gemini seed on Neon; #7.

### 2026-10-31 — #9 PR 1 implemented
- Done: T001–T027 on `feat/9-chat-web-foundation` (4 semantic commits); tests first; guard and
  dropped-stream tests mutation-checked; dev smoke on the mock OK.
- Fixed: harden config (origin-based prefixes), `@source` path, server/client split of i18n.
- Review: QA (request changes) + senior (approve with changes) applied: empty bubble/typing
  indicator, finish without `finishReason` no longer flagged as dropped, focus, more hostile cases.
- Next: user merges PR 1; then PR 2 (US2+US3).

### 2026-10-31 — #6 PR 1 (agent core)
- Done: settings, agent state with atomic lockout, payment/hours/PII rules, router (Jev + Haiku
  fallback, one budget), fake models, tool registry, stream adapter, `/api/chat`, tools for
  products, payments, policies, store info and orders, 29 scenarios, DL-011 outcome.
- Fixed: pool rolled back the reserved attempt when a tool raised (commit inside the state calls).
- Next: review PR, then user runs `python -m evals.router_spike`, `--live`, Neon seed (T032) and
  the manual UI check; then #7 (PR 2) and #8 (PR 3).

### 2026-10-31 — Retrieval (#5 PR B)
- Done: embeddings (fake, Gemini over httpx, cache), policy PDF chunking, product docs, hybrid
  RRF search (`search_policies`, `search_products`, `similar_to_product`), connection pool, seed
  wired to the index, tests, README Data section, DL-010.
- Fixed: stemmer gap (devolver/devolução) via 5-char prefix match; fake guard now keyed on remote
  target.
- Next: open the PR (two-reviewer gate); T032 seed Neon with Gemini (needs the user's keys), then
  #6 agent core plan/tasks.

### 2026-10-31 — #9 spec review applied
- Done: merged main into `dinorahfariasc/chat-web`; applied the PR #32 review to
  `specs/003-chat-web/*`; decision log entry renumbered to DL-009; contract doc now says cards in #9.
- Fixed: Streamdown 2.7.1 defaults allow any image/link (`*`), so they are overridden. ai@7 ends a dropped
  stream as `ready` with no error, so it is detected in `onFinish`.
- #32 merged; handoff points the next session at PR 1 (T001–T028).
- Next: implement #9 PR 1 in the `chat-web` worktree.

### 2026-10-31 — Day 1 wrap-up
- Done: scaffolding + production skeleton (#3), chat stream contract (#4), Gemini embeddings
  (DL-007), store ETL + quality report + safe seed (#31), 002 agent-core spec drafted, 003
  chat-web spec PR #32 reviewed (blocker: block markdown images), handoff docs (#33).
- Fixed: Vercel env vars only apply to new deployments; stacked squash-merge conflicts resolved
  with `rebase --onto`.
- Next: #5 PR B (retrieval + Neon seed); apply review to #32 and merge; 002 plan/tasks/review.

### 2026-10-31 — #9 PR 3 (mobile + polish)
- Done: viewport-fit cover + safe-area padding (bottom and sides), catalog-only copy, audits
  clean, prod fail-closed checked by hand. Review (QA + senior) approved; side insets applied.
- Gotcha: a PR stacked on another merges into the base branch; it only reached main because it
  merged before the base was squashed. Retarget stacked PRs to main before merging.
- Next: user does T046 (375 px screenshot) and merges; then #6 agent core.

### 2026-10-31 — #9 PR 2 (tools, cards, errors)
- Done: tool status, product cards, 401/429/budget/retry states, `/login` placeholder; 90 tests.
- Review: QA approve, senior approve with minors (countdown remount key, rate-limit flag reset,
  announced tool state) — applied.
- Next: user merges #36 then PR 2 (retarget to main after #36 squash: `rebase --onto`); PR 3.
