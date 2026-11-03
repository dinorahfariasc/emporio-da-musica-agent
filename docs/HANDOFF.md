# Handoff — how to continue this project with any AI agent

Read this first, then `CLAUDE.md` (rules), `.specify/memory/constitution.md` (principles) and
`docs/decision-log.md` (why things are the way they are). This file is the **current state**;
update it at the end of every work session.

_Last updated: 2026-11-02 18h00 (all P0 complete, ready to tag and ship)._

## 1. What this is

A customer-service agent ("Melody") for a fictional music store,
**Empório da Música**. Data: `inputs/data/`.
Deliverables: public repo with real commit history, README (run instructions, decisions,
limitations, **AI-assistant workflow**), 3–5 example conversations. **Final deadline: 2026-11-02 18:00
(America/Campo_Grande), with P0, P1 and P2 all done. Target: P0 in production by 2026-11-01 evening, then
P1/P2 on 11-02. The brief forbids any change to the repo after the delivery time.**
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

_Last updated 2026-11-02._

**On `main` (all P0 merged):** data foundation (#35) · chat web (#36–#38) · agent core (#40) ·
actions (#42) · MCP (#43) · auth, limits, deploy config (#44) · CI fix (#50) · README and
deliverables (#48, #55, #58) · branding and approved Melody UI (#46, #49, #51) · Docker Compose
(#52, #53) · exact stock (#54) · prompt fixes (#56) · history in the browser (#57) · store home
with the Melody widget (#59) · customer lookup by contact, order context, sale calendar,
pre-sale for coming-soon products, totals for several units in Python (#60).

**Issues:** closed #5, #6, #13, #18 (2026-11-02, each with a comment linking its PRs and any
criterion superseded by a later decision). Open: #11 (tag `v1.0-submission` at the deadline,
working production), #12 (server-side history; browser history done in #57), P1/P2 #14, #15,
#16, #17, #19, #21, #23.

**Production (Vercel) is DOWN since #44:** the frontend's fail-closed hook throws
`missing required config: BACKEND_URL`. `AUTH_SECRET`/`SERVICE_JWT_SECRET` are not set in Vercel
yet; `BACKEND_URL` comes from the service binding, which seems not visible to
`src/instrumentation.ts`. Checklist in README "Run in production". Deferred by Dinorah; local
Docker is the working path.

**Pending on Neon (Dinorah runs it, needs the Neon and Gemini credentials):** re-seed after #60 so
product 130 is sellable on pre-sale: `cd backend && uv run python -m etl --yes` with
`DATABASE_URL_UNPOOLED` (Neon direct URL), `EMBEDDINGS_PROVIDER=gemini` and `GEMINI_API_KEY`.
Vectors are cached, so it costs no embedding calls.

**Models (DL-012):** router `perplexity/pplx-decider-v1.2`, specialist `openai/gpt-6-luna`,
general `deepseek/deepseek-v4.1-flash`, all through OpenRouter.

**Rules decided since the brief (see the decision log):** WhatsApp (67) 3321-4500 separate from
the phone (67) 3341-4444 and a R$ 100,00 minimum instalment from 4x (DL-FE-005); coming-soon =
pre-sale, no immediate delivery, no date, no reservation (DL-BE-006); a name alone never unlocks
orders, only the e-mail or phone on file (DL-BE-005).

**Next:** spec `010-semantic-recommendations` (style not in the catalog → top 3 similar with
shared/different traits, or a friendly tour of the catalog when nothing is close). Needs real
embeddings locally (`EMBEDDINGS_PROVIDER=gemini` + `GEMINI_API_KEY` in `backend/.env`) to
calibrate the similarity thresholds; the local Docker index uses the fake embedder. Then the
Vercel deploy.

**Local testing:** `docker compose up --build` (README). Test accounts `probe`, `probe2`, `probe3`
exist only in the local Docker database (for scripted batches; each has the 200k tokens/day cap).

## 3b. UI track (Figma ready) — read before touching `frontend/`

The Figma file is ready and #18 applies it. Spec: `specs/008-figma-branding`. Brief: `docs/design/figma-brief.md`. Decisions: `DL-FE-001` (fallback, superseded) and `DL-FE-002` (approved Melody UI: Inter, action `#E00B41`, light + dark with a header theme toggle). Visual QA: `pnpm dev` (or `CHAT_MODE=mock pnpm dev`), sign in, open `/dev/gallery` (DEV only, 404 in production). `CHAT_MODE=mock` only mocks the chat backend; login is still required (create a local user with `scripts/create-user.ts`).

- **#44 and #13 are not on `main` yet.** They still own login-form, Sign out, PT/EN, `en.ts`. **Merge order: #44 → #13 (rebased) → any leftover branding chrome.** Current-surface restyle (tokens, empty/conversation/tools/cards/input/errors, placeholder login, header without Sign out/PT-EN) proceeds on `main` in parallel; expect a rebase when those land.
- Open PRs that still conflict if edited now: #44 edits `src/app/login/page.tsx`, `src/components/login/login-form.tsx`, `src/components/chat/chat-header.tsx`, `src/lib/i18n/pt-BR.ts`, `src/app/api/chat/route.ts`, `src/proxy.ts`; #13 (worktree `track-c-frontend-i18n-brand`, not yet a PR) edits `layout.tsx`, `login/page.tsx`, `chat-header.tsx`, `product-card.tsx`, `lib/i18n/*` and adds `en.ts`, `language-switch.tsx`.
- **Safe to do now (no overlap):** design tokens in `src/app/globals.css`, Tailwind theme, fonts, logo asset in `public/`, new presentational components under `src/components/ui/`.
- **Do not touch:** `frontend/auth.ts`, `src/lib/auth/*`, `src/proxy.ts`, `src/app/api/**`, `scripts/create-user.ts` (auth), and the chat-stream logic (`src/lib/chat/*`, tool labels). Restyle, never re-wire.
- **Copy:** all strings go through the i18n catalog (pt-BR default, EN via `en.ts` after #13). No hard-coded text in components.
- **Constraints that must survive the restyle:** 375 px without horizontal scroll, tap targets ≥ 44 px, safe-area insets, `role="status"` announcements, no images in markdown, product cards without images, no status codes or JSON shown. Prices are only formatted, never computed.
- **Gate per PR:** `pnpm lint && pnpm typecheck && pnpm test && pnpm build`; `/` and `/login` must still prerender. Decision-log prefix `DL-FE-NNN`. Small PRs, `Part of #18`.
- **Backend/agent files are off limits for this track** (other agents work there: `backend/app/**`, `backend/evals/**`).

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
- **Decision log numbering:** DL-001..DL-013 are sequential and stay. New entries use per-area ids so parallel branches do not collide: `DL-BE-001` (backend/agent), `DL-FE-001` (frontend), `DL-DOCS-001` (docs, specs, README), `DL-DATA-001` (data/EDA). Take the next free number inside your own prefix.
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
- CSV files use CRLF line endings; never rewrite them (`inputs/** -text`).
- A PR whose base is another PR's branch merges into that branch, not into `main` (#41 did). Retarget to `main` before merging, or cherry-pick onto `main` afterwards.
- Live evals: one event loop (`evals/runner.py::_live_client`); decider models are not chat models (`/api/alpha/decisions`); DeepSeek needs reasoning off for the router.
- Squash-merged stacked PRs conflict: retarget with
  `git rebase --onto origin/main <old-base> <branch>` then `git push --force-with-lease`.
- Vercel Services: the backend is **private**; reach it from Next.js route handlers via
  `BACKEND_URL` (binding). `/mcp` will need its own public rewrite (issue #8).
- Docker: never bind-mount `./backend` over `/app` (the macOS `.venv` breaks `pydantic_core`
  in Linux). `LLM_PROVIDER=fake` is test-only: in the chat every turn fails with `AssertionError`.
- Local `uv run pytest` needs `uv sync --group etl` (tests import `etl/`, which needs `pypdf`).
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

### 2026-11-03 — Specific-product answers and order context (DL-BE-009)
- **Fixed:** payment calculation by name (no more false "Não consegui consultar agora" tag when the model asks for installments in the same step as get_product); a question about one product no longer lists every promotion (prompt + tool docstring); the items of an order looked up earlier now survive in the history, so Melody stops guessing the product from earlier chat. Backend rebuilt locally, 388 tests pass.
- **Next:** commit on its own branch/PR (not on `docs/project-overview`); screenshots for the overview PDF.

### 2026-11-03 — Issues review, models documented
- **Done:** commented all open issues with the decision; closed #16 (Playwright) and #17 (routing bench) as not planned (DL-DOCS-002); "Models used" section in both READMEs; empty-alternatives wording fix in the prompt (pushed on `feat/mcp-read-only`, no PR yet).
- **Next:** open the PR so CI runs; fix issue numbers in README "Limitations" (HITL is #14, judge is #23); commit the uncommitted UI changes (Melody avatar, FAB, greeting bubble, refresh icon).

### 2026-11-02 — MCP read-only, semantic recommendations, PT README, diagrams
- **Done:** MCP exposes only 7 read-only tools (DL-BE-007); `find_similar_products` takes `category_id`, prompt translates subjective requests, scenarios us4-5/us4-6 (spec 010, DL-BE-008); `README.pt-BR.md` and Mermaid diagrams (`docs/architecture.md`, embedded in both READMEs); JWT kept, documented as built for an open deploy.
- **Rule:** any README change must be mirrored in `README.pt-BR.md`.
- **Next (owner, needs keys):** spec 010 T5, `uv run python -m evals --live` and a few subjective chat requests; DB tests must use a separate DB (`emporio_test`), since `seeded_db` re-seeds with fake embeddings and would overwrite the Docker DB's Gemini ones.

### 2026-11-02 — Final Audit & Status Update
- **Done:** Reviewed all P0 epics (E0–E6) against the brief. All requirements met: agent functional, 5 live examples covering all 4 brief scenarios + security test, README complete with setup/decisions/workflow/limits. 60 commits, clean history, no force-pushes.
- **Status:** P0 ready to ship. Production Vercel has startup issue (BACKEND_URL visibility) documented in README; local Docker is fully functional. Tag `v1.0-submission` is the last step before going public.
- **Next:** User creates the tag, makes repo public, sends delivery link by 18:00 deadline.

### 2026-11-02 — #18 store home PR
- **Done:** DL-FE-005 assumptions applied (e-mail without accent, minimum instalment R$ 100,00, phone and WhatsApp distinct); gate green; `feat/store-home` pushed and PR opened.
- **Next:** store confirms DL-FE-005; if confirmed, align the backend policy text (4x–6x minimum) with the page.

### 2026-11-02 — Pre-sale, issues, handoff
- **Done:** #60 merged with coming-soon pre-sale (DL-BE-006) and `calculate_payment_options(quantity)`. Issues #5, #6, #13, #18 closed with PR links; progress comments on #11 and #12. Status section rewritten.
- **Pending:** Neon re-seed (Dinorah, credentials). Vercel deploy still down.
- **Next:** spec 010 semantic recommendations.

### 2026-11-02 — Hard-case batch, customer lookup, #59 review
- **Done:** #59 review fixes (Melody aligned with the page on WhatsApp/instalments, mobile minimised, catalog copy). `find_my_orders` (contact-based lookup, name only disambiguates), order region/age/payment, sale-calendar answers (DL-BE-005).
- **Fixed:** Melody wavering on a discontinued product; promising reservations; "Política de trocas consultada" for every manual lookup.
- **Next:** spec 010 semantic recommendations (needs a Gemini key locally). Local test accounts `probe`/`probe2` exist only in the Docker DB.

### 2026-11-01 — Review against the brief
- **Done:** 11 live conversations against the brief; five recorded as the example conversations (`docs/conversations/`, replacing the fake-mode placeholders). README: interface row, history persistence, Assumptions, Access for reviewers.
- **Fixed:** prompt (persona greeting, alternatives when out of stock, defect rules before handoff, no preamble) #56; history in `localStorage` + New chat + one card per product #57.
- **Next:** #56 and #57 both append to `docs/decision-log.md` — rebase the second one. Then the Vercel deploy.

### 2026-11-01 — #18 store home (`feat/store-home`, spec 009)
- **Done:** `/` is a public, static store page (about, hours, contact, payment, returns, shipping, promotions, warranty, privacy from manual v2.1, PT/EN); Melody moved to a side panel (≥ 1024 px) / full-screen sheet (mobile) that minimises to a FAB with an unread dot; state in `<html data-chat>` + localStorage. DL-FE-004.
- **Auth:** only `src/proxy.ts` (+ `src/lib/routes.ts`) lets `/` through; signed out, the widget links to `/login?callbackUrl=%2F`. `/api/chat`, `src/lib/auth/*` and backend untouched.
- **Gallery:** `/dev/gallery?screen=<chat screen>&frame=widget` and `screen=widget-signin`.
- **Assumptions (DL-FE-005, Dinorah 2026-11-02, to be confirmed by the store):** e-mail without accent; minimum instalment R$ 100,00 (also 4x–6x); phone (67) 3341-4444 and WhatsApp (67) 3321-4500 are distinct channels. Melody's backend knowledge may still say R$ 80,00 for 4x–6x.
- **Rebased on main (#56–#58):** the kept conversation (DL-FE-003) works in the widget: "New chat" in Melody's header, Sign out clears it, a restored conversation is not "unread".
- **Round 3:** chat open by default on desktop and mobile (saved "minimised" wins); desktop maximise/restore (full-window modal, Esc restores, not saved, same chat instance).
- **Round 2:** music-staff background (`music-staff-background.tsx`, `.staff-bg` in `globals.css`), card hovers (`.store-card`), menu wraps next to the panel, e-mail wraps after "@". Do not run `pnpm build` while `pnpm dev` is running in the same folder: it replaces `.next` and the dev server serves the page without CSS until restarted.
- **Next:** store confirms the DL-FE-005 assumptions.

### 2026-11-01 — Docker, stock quantity, README
- **Done:** Docker Compose for db + backend + frontend (#52, #53); end-to-end login + chat verified locally with OpenRouter. README: Docker quickstart, env-var table, production status, new decisions.
- **Fixed:** compose forced the fake LLM (every turn failed); host bind mounts broke the container venv; agent could not state stock counts (#54, `get_product(quantity=N)` → `enough_stock`).
- **Next:** fix the Vercel deploy (secrets + `BACKEND_URL` visibility at startup), then create the reviewer login on Neon.

### 2026-11-01 — #18 approved Melody UI (`feat/ui-melody`)
- **Done:** approved tokens (Inter, `#E00B41`, light + dark), components, `/` and `/login` states, PT | EN with `en.ts`, DEV gallery `/dev/gallery`; DL-FE-002; 008 spec/plan/tasks updated. Gate green; `/` and `/login` still prerender.
- **Fixed:** tests that asserted `role="alert"` or old copy now use `data-testid` / catalog keys.
- **Added:** header theme toggle (sun = light, moon = dark; localStorage `melody-theme`, OS preference by default; no-flash inline script in `layout.tsx`, dark tokens under `:root[data-theme="dark"]`). Below 420 px the header store name is `sr-only` so the toggle fits. `search_policies` done label follows the design ("Política de trocas consultada" / "Return policy checked").
- **Next:** Dinorah reviews, commits and opens the PR; reconcile `en.ts` / language switch with #13; lockout copy needs an auth signal (gallery-only today).

### 2026-11-01 — EDA notebook (#22, track D)
- **Done:** `analysis/` (notebook, HTML export, generator, README) and `specs/007-eda-notebook/`; no anomalies beyond the data quality report; DL-DATA-001.
- **Next:** review and merge.

### 2026-11-01 — #18 Figma branding (spec 008)
- **Done:** `specs/008-figma-branding` (spec/plan/tasks); `DL-FE-001`; 003 notes and backlog S13 pointed at 008. Current chat surfaces restyled on a follow-up PR (tokens, mark, empty/conversation/errors/placeholder login). Figma MCP rate-limited — fallback palette documented.
- **Fixed:** none.
- **Next:** rebase login form / Sign out / PT-EN after #44 → #13; re-read Figma when quota allows.

### 2026-11-01 — #42 merged; deadline confirmed
- **Done:** #42 (actions) merged into `main`. User confirmed the final deadline: 2026-11-02 18:00 (America/Campo_Grande) with P0, P1 and P2 all done.
- **Done (cont.):** DL numbering is now per area (BE/FE/DOCS/DATA). Three parallel worktrees started: track A (spec 004 / #10), track B (MCP #8, then HITL #14), track C (frontend #13, #18; checks #20 is covered by #37, which closed with PR 2 US2 cards).
- **Done (cont.):** Neon seed (T032) done by the user: 7.24 s, counts and checksums match local; #43 (MCP) merged.
- **Done (cont.):** track status: #44 (spec 004 + code) open; track D (EDA, DL-DATA-001), E (router benchmark + judge, DL-BE) and F (README draft, delivery checklist) done locally, not pushed; #13 i18n implemented but uncommitted in its worktree. UI work moves to a separate agent (section 3b). `MCP_API_KEY` is set in Vercel; redeploy pending.
- **Next:** #11 README + example conversations after the deploy is stable; #12, #15, #19, then P2 (#22, #23, #21).
### 2026-11-01 — #8 MCP server (PR 3 of 002, track B)
- **Done:** `backend/app/mcp.py` exposes all 12 contract tools over MCP streamable HTTP at `/mcp`, bearer-authed (`MCP_API_KEY`, disabled when unset), mounted in `app/main.py` with a combined lifespan; `vercel.json` `/mcp` rewrite; README "Use the store tools from Claude Desktop" section; `tests/test_mcp.py` (tools/list parity, no `ctx` in the schema, 401 on missing/wrong key); DL-BE-001; T034–T036 checked off; 290 backend tests pass, ruff clean. Merged to `main` as #43.
- **Next:** #14 human-in-the-loop confirmation for write actions needs a short spec/plan/tasks first (ask the user: addition to 002 or a new small spec).

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
