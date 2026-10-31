# Handoff — how to continue this project with any AI agent

Read this first, then `CLAUDE.md` (rules), `.specify/memory/constitution.md` (principles) and
`docs/decision-log.md` (why things are the way they are). This file is the **current state**;
update it at the end of every work session.

_Last updated: 2026-10-31._

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

**Merged to `main`:** #2 bootstrap · #3 scaffolding + production walking skeleton · #4 chat stream
contract · embeddings switch to Gemini · #5 spec + first implementation PR (store ETL, data-quality
report, safe seed) · #32 003 chat-web spec (spec, plan, tasks; review applied).

**In flight (check `gh pr list` and the board for the truth):**
- **#5 PR B** (retrieval): T021–T031 implemented on branch `feat/5-retrieval` (97 tests pass
  locally); PR to open and review. Remaining: T032 (manual: seed Neon with Gemini, user holds the
  keys) and T033 polish (README/DL-010 done; tick the issue #5 criteria after the Neon seed).
- **#9 chat web:** spec merged (#32). **Next: implementation PR 1 — Foundation + US1, tasks
  T001–T028** in `specs/003-chat-web/tasks.md` (worktree `chat-web`, new branch from `main`).
  Read first: `spec.md` (FR-001…FR-019), `research.md` R2 (error mapping + dropped stream), R4
  (**hardened Streamdown — mandatory**), R10 (Cache Components), R11 (fail-closed `chatMode()`),
  R12 (double-send guard). Tests first; `pnpm lint && pnpm typecheck && pnpm test && pnpm build`
  green; PR body `Part of #9`; QA + senior review before merge. Then PR 2 (US2+US3, T029–T041)
  and PR 3 (US4+polish, T042–T047, `Closes #9`).
- **#6 agent core:** spec written on branch `docs/6-agent-core-spec` (not merged, no PR yet).
  Next: `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze`, then PR + review. Depends on the
  retrieval API in `specs/001-data-foundation/contracts/retrieval-api.md`.
- **Not started:** #7 actions, #8 MCP, #10 auth/limits/deploy, #11 README + example conversations.

**Remaining P0 order:** finish #5 PR B → #6 (+#7, #8) → #9 UI → #10 → #11. Do P1/P2 only after
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
- **Decision log numbering:** next free is DL-009 (check the file; parallel branches collide).
- **Facts from the system:** prices, stock, promos, eligibility are computed in Python, never by
  the LLM (constitution I).
- Update the board status and this file as you go.

## 5. Environment

| Item | Notes |
|---|---|
| Local DB | `docker compose up -d --wait` → Postgres 16 + pgvector on **localhost:5433** (override with `POSTGRES_PORT`; another project may hold 5432/5433) |
| Backend | `cd backend && cp .env.example .env && uv sync && uv run pytest` — no keys needed (fake providers by default) |
| Frontend | `cd frontend && cp .env.example .env.local && pnpm install && pnpm dev` (`CHAT_MODE=mock` replays fixtures; **production must use `backend`**) |
| Secrets (never commit) | `GEMINI_API_KEY` (embeddings, free tier), `ANTHROPIC_API_KEY`, `TYPESAFE_API_KEY` (Jev router). Production values live in Vercel env vars; the user holds the keys. |
| Neon (prod DB) | Vercel Marketplace integration; vars `DATABASE_URL` (pooled) and `DATABASE_URL_UNPOOLED` (use for seed/DDL). Region São Paulo; Vercel functions run in `iad1` (latency follow-up: move to `gru1`). |
| Vercel | Single project `emporio-da-musica-agent`; env changes only reach deployments created afterwards (redeploy). Production redeploys must be run by the user. |
| CLI auth | `gh` is logged in as `dinorahfariasc` (scopes include `project`); `npx vercel login` done on the user's machine. |

## 6. Gotchas learned the hard way

- **Versions are newer than most docs:** ai@7 (not v5), Next 16 with Cache Components (no
  `export const dynamic`; use `await connection()`), Vitest 5. Check `node_modules` types and
  `node_modules/next/dist/docs` before using an API.
- `.env*` ignore rules hide `.env.example`; keep the explicit `!.env.example`.
- CSV files use CRLF line endings; never rewrite them (`challenge/** -text`).
- Squash-merged stacked PRs conflict: retarget with
  `git rebase --onto origin/main <old-base> <branch>` then `git push --force-with-lease`.
- Vercel Services: the backend is **private**; reach it from Next.js route handlers via
  `BACKEND_URL` (binding). `/mcp` will need its own public rewrite (issue #8).
- Voyage was rejected (needs a card); embeddings are Gemini `gemini-embedding-001`, 768 dims.
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
