# Decision Log

Living record of how this project's decisions were made, which alternatives were considered,
and how AI assistants took part in the process. Updated throughout development; the README
summarizes it and links here.

**Entry format:** context → decision → alternatives → rationale → role of AI.

---

## DL-001 — Kickoff: reading the brief and the data (2026-10-31)

**Context.** Artefact technical challenge (AI Engineer): a customer-service agent for the
fictional store Empório da Música, backed by operational CSVs and a policies manual (PDF).
Deadline: P0 done by 2026-10-31 evening; 2026-11-02 reserved for improvements.

**What was done.** Full read of the brief, the manual (8 pages) and profiling of the 6 CSVs.
Several inconsistencies were found; handling them became data requirements:

| Source | Finding |
|---|---|
| products | IDs 135–144: name contradicts description (e.g. "Music Man Bass 1X" described as a Fender Jazz Bass); specs contradict description (5 vs 4 strings, 88 vs 61 keys); `specs` JSON schema varies by category |
| products | 96 `active` with zero stock; 113 `discontinued`; 136 `discontinued` with 13 units; 130 `coming_soon` yet present in orders |
| promotions | Duplicates per product (96: 18% and 40%); only 4 active (90, 94, 121, 127); no validity dates |
| orders | Totals differ from the sum of items (order 3: 3498 vs 3450; order 20: 1488 vs 1400) |
| customers | "Ponta Porã" stored with two different Unicode encodings; customers 11 and 43 share the email `bruno.martins@jmail.com` (found in backlog QA review) |
| manual | Two WhatsApp numbers (3341-4444 in §1.2, 3321-4500 in §7); email with and without accent; installment table contradicts §3.1; 7-day withdrawal right applies only to online purchases, but orders don't record the channel |

Challenge files were renamed to paths without spaces/accents (`challenge/`,
`challenge/data/*.csv`, `store_policies.pdf`).

**Role of AI.** Claude Code read the PDFs and CSVs and produced the profiling; I validated the
findings.

---

## DL-002 — Architecture and workflow defined in a "grilling" session (2026-10-31)

**Context.** Before specifying anything, I used a *grilling* skill (a structured interview in
rounds, each question carrying a recommended answer) to settle the decision tree. The job
description was used as the baseline of what is expected (LangGraph, Vercel AI SDK, MCP,
assistants that execute tasks, AI in production).

### Decisions

| Topic | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| Orchestration | **LangGraph** | Plain SDK, PydanticAI, LangChain agents | The flow is naturally a graph: router → specialized nodes → fallback (conditional edge). Named in the job description. |
| Routing | **Jev (TypeSafe AI)** as intent classifier, **Claude Haiku (structured output) as fallback** | LLM-only routing | Typed decision with confidence, in milliseconds and at near-zero cost; LLMs only write answers or handle ambiguity. Jev × Haiku comparison goes into the README. |
| LLMs | **Claude Haiku 4.5** writes answers for specialized nodes; **Claude Sonnet 5.5** in a ReAct agent for low confidence / multi-intent | One model for everything | Cost and latency proportional to difficulty. |
| Data access | **Deterministic** tools with parameterized SQL; price/stock/discount computed in Python | Text-to-SQL agent | The manual forbids quoting price/stock without checking the system; text-to-SQL is non-deterministic. |
| Policies | **Hybrid RAG** (Postgres full-text + pgvector), one chunk per manual section | Whole manual in the prompt; BM25 only | Manual is small, but the architecture must scale; semantic search works across languages. |
| Embeddings | **Voyage AI** (free tier) | Local fastembed, Gemini, no vectors | Anthropic has no embeddings API; a local model doesn't fit a serverless function. |
| Recommendation | `find_similar_products`: structured filters + vector similarity | Name search only | "We don't carry guitar X, but here are similar ones" — fulfils manual §7.3 (suggest alternatives). |
| Tools | Exposed through an **MCP server** (FastMCP) mounted in FastAPI | Direct function calls | Named in the job description; the same server can be used from Claude Desktop/Code. |
| Actions | `request_return`, `register_complaint`, `handoff_to_human`; confirmation via `interrupt` (P1) | Answer-only agent | Job description asks for assistants that execute tasks. |
| Identity | Orders are revealed only with order number + email or phone | Trust the logged-in user | LGPD; the logged-in user is the evaluator, not the customer. |
| Persona | **Melody**, informal-but-professional tone (manual §7.1), §7.2 flow, multilingual | — | Visuals/branding will come from a Figma mockup later. |
| Dates | Use the **real current date** | Configurable reference date | Simplicity; accepted consequence: returns for dataset orders will be refused as out of window. |
| Frontend | **Next.js + Vercel AI SDK (`useChat`) + shadcn/ui**, i18n PT/EN | CLI, Streamlit | Production-like deliverable; AI SDK named in the job description. |
| Deploy | **Everything on Vercel** (Next.js + Python functions) + **Neon Postgres** (free) | Railway, HF Spaces, Fly | Free, single deploy and single database; low traffic. |
| Access | Login without public sign-up (accounts created by script) + daily token budget and rate limit | Open to the public | A paid API key is exposed. |
| Quality | pytest (fake LLM/Jev), reference-conversation evals, GitHub Actions CI; guardrails P0; Langfuse P1 | — | "What works in production". |
| Data (ETL) | `etl/` module with Pydantic validation, explicit correction rules and a generated report | Ad hoc cleanup | Reproducible and testable. |

### Data correction rules
- Order total mismatch: keep the original `total_brl` (amount paid) and flag it.
- Name × description: the **name** wins; contradictory descriptions are not shown.
- Specs × description: **specs** win.
- Promotions: only `is_active=1`; if several are active, the largest applies.
- `discontinued` is not for sale; zero stock = unavailable (suggest alternatives); `coming_soon` = "coming soon".
- Official contact: §1.2 (67) 3341-4444; email without accent; conflict documented.
- Installments: §3.1 overrides the table.
- Text normalized to Unicode NFC.

### Priorities
- **P0 (by 11/01 evening):** full agent, backend + MCP, Next.js chat with login, deploy, README, decision log, 3–5 conversations.
- **P1:** refined token limits, persisted history, i18n, `interrupt`, Langfuse, Playwright, MCP demo in Claude Desktop.
- **P2 (11/02):** admin dashboard (charts + insights chat), EDA notebook, LLM-as-judge.

### Process
- **Spec-Driven Development with Spec Kit**: constitution → one spec per epic
  (`001-data-foundation`, `002-agent-core`, `003-chat-web`, `004-auth-limits-deploy`,
  `005-admin-dashboard`) → plan → tasks.
- **Agile on GitHub**: tasks become draft issues, reviewed by two agents (QA and senior
  engineering) before being created in GitHub Projects; PRs use `Closes #n`.
- **Parallelization**: backend and frontend in separate worktrees (Orca) once specs exist.
- Example conversations are **generated** by a script against the real agent (they double as
  evals), including non-obvious scenarios (prompt injection, someone else's order, PIX + promo,
  discontinued product with stock, language switch).

**Role of AI.** Claude Code ran the grilling (questions + recommendations); the decisions were
mine. Research on Jev was done by the agent through web search.

---

## DL-003 — Language policy and roadmap-first backlog (2026-10-31)

**Decision.** Everything is written in English (code, docs, commits, PRs, issues) except the
agent persona and the website copy, which are Portuguese-first (site with PT/EN switch; the
agent answers in the customer's language).

**Decision.** The backlog is created top-down: epic issues now (one per Spec Kit epic, plus
P1/P2 items) so branches and PRs can be linked from day one; task-level issues are generated
from each epic's `tasks.md` and attached as sub-issues once the spec is approved.

**Role of AI.** Epic drafts written by Claude Code and reviewed by two reviewer agents (QA and
senior engineer), both "approve with changes". Their findings reshaped the plan: platform risk
moved to the start (walking-skeleton deploy), a written chat stream contract enables parallel
backend/frontend work, the agent epic was split, and acceptance criteria became concrete
(numeric payment cases, identity edge cases, named injection attacks). See the review log in
`docs/planning/backlog.md`.

---

## DL-004 — Scaffolding and deployment topology (2026-10-31, #3)

| Decision | Alternatives | Rationale |
|---|---|---|
| **One Vercel project with Services** (Beta): `frontend` (Next.js) is the only public service; `backend` (FastAPI) is private and reached through a service binding (`BACKEND_URL`) | Two Vercel projects (web + api), the initial choice | Vercel detected the monorepo and suggested Services. A private backend with an internal binding *is* the BFF pattern recommended in the backlog review: no CORS, no public API surface, one domain and one place for firewall/protection. `/mcp` will get its own public rewrite in #8. Walking-skeleton routes (`/api/health`, `/api/stream-test`) live in Next.js and proxy to the backend, so they exercise the full browser → Next.js → FastAPI → Neon path. |
| Backend as a flat `app/` package, entrypoint `app.main:app` via `[tool.vercel] entrypoint` | `src/` layout with an installed package | Vercel imports the module from the project root; a non-installed flat package avoids relying on the build installing the project itself. |
| Python 3.13 | 3.12 (Vercel default) | Supported by Vercel and already installed locally. |
| Providers selected by env (`LLM_PROVIDER`, `ROUTER_PROVIDER`, `EMBEDDINGS_PROVIDER`), defaulting to `fake` | Real providers by default | CI and fresh clones run with no API keys (constitution IV). |
| Local Postgres published on port 5433 (configurable via `POSTGRES_PORT`) | 5432 | Avoids clashing with a Postgres already running on the developer machine. |
| DB connections use `prepare_threshold=None` | Default psycopg prepared statements | Neon's pooled endpoint (PgBouncer, transaction mode) does not support server-side prepared statements. |

**Role of AI.** Claude Code checked Vercel's current Python runtime and Services docs (500 MB
bundle limit, zero-config FastAPI, streaming, bindings) and proposed switching to Services after
Vercel's own detection suggested it; I confirmed service names, public routes and bindings.
Also found: Next.js 16 enables Cache Components, so dynamic route handlers use `connection()`
instead of the removed `dynamic` segment config.

**Walking skeleton verified in production (2026-10-31).** `https://emporio-da-musica-agent.vercel.app`
- `/api/stream-test`: 10 SSE chunks arrive ~300 ms apart in the client — no buffering across
  browser → Next.js → service binding → FastAPI.
- `/api/health`: `{"status":"ok","db":"ok"}` against Neon.
- Backend function bundle: **12.9 MB** (limit 500 MB); frontend functions ~0.6 MB.
- Latency: health cold ~3.1 s, warm ~1.7 s (opens a new DB connection per request, functions run
  in `iad1`); plain streaming warm ~0.4 s to first byte. Follow-ups: reuse connections and
  co-locate the function region with the Neon region.
- Lessons: Neon Marketplace env vars only reach deployments created *after* they exist (needed a
  production redeploy); `vercel link` and create-next-app add `.env*` ignores that also hide
  `.env.example`, fixed with an explicit `!.env.example`.

---

## DL-005 — Data foundation spec, plan and tasks (2026-10-31, #5)

**Context.** Spec Kit artifacts for epic 001 (`specs/001-data-foundation/`), written against
the #3 scaffolding (flat `backend/app/`, ETL in `backend/etl/`).

**Correction to DL-001.** Both "Ponta Porã" values are already NFC; there are not two Unicode
encodings. The CSVs use CRLF line endings and the last row has no trailing newline, so the
`cut`-based profiling saw "Ponta Porã\r" (5 rows) and "Ponta Porã" (1 row) as different values.
NFC normalization stays (it is tested with a decomposed fixture), CSV parsing must handle CRLF and
a missing final newline (tested with a CRLF fixture), and the report shows the real NFC count (0).

**New finding.** Categories 6, 7 and 8 (woodwinds, brass, orchestral strings) have no products,
although the manual says the store sells them. This is reported as an informational anomaly.

| Decision | Alternatives | Rationale |
|---|---|---|
| Seed reloads only the tables it owns, in one transaction, with `TRUNCATE` **without** `CASCADE` | Drop/recreate schema; upsert by ID | Re-seeding production must never touch other epics' tables (users, history, usage). |
| Seed-time embedding failure: retry, then abort (store unchanged) | Load without vectors; fall back to the fake | No half-built vector index in production; query-time full-text fallback covers runtime outages. |
| One persistent `embedding_cache` table for query and document embeddings | In-memory LRU | Survives serverless cold starts; re-seeding makes no provider calls. |
| Provider: `gemini-embedding-001` at 768 dims (normalized after truncation), direct REST via httpx (see DL-007) | SDK; 3072 dims | Free tier is ample for about 90 documents plus cached queries; fewer dependencies. |
| Fake embedder = hashed character n-grams | Random vector per text | Makes the CI retrieval check (§4.1 in top 3) meaningful instead of chance. |
| Hybrid ranking with Reciprocal Rank Fusion (k=60), exact scan, `pt_unaccent` full-text | Weighted score sum; HNSW index | No score calibration; the corpus is tiny; accent-less queries work. |
| Policy chunks per subsection, validated against a hard-coded table of contents | Free-form splitting | Citable "§4.1"; extraction errors fail loudly. |
| Purchase channel missing on orders is reported as an anomaly | Ignore | The 7-day withdrawal right (§4.1) depends on it; the agent must ask the customer. |

**Role of AI.** Claude Code ran the Spec Kit commands (specify, clarify, plan, tasks, analyze),
profiled the data and the PDF, and proposed the options. I answered the four clarification
questions and approved the remediation. The cross-artifact analysis caught a `CASCADE` truncation
that could have emptied other features' tables, and a DL-001 conflict missing from the anomaly
catalogue.

---

## DL-006 — Chat stream contract (2026-10-31, #4)

| Decision | Alternatives | Rationale |
|---|---|---|
| Use the **AI SDK UI message stream protocol v1** as-is, documented in `docs/contracts/chat-stream.md` | Custom SSE format + adapter in the frontend | `useChat` consumes it natively; tool and data parts come for free. Verified against the installed `ai@7` type definitions, not only the docs page (which described v5). |
| Shared fixtures in a repo-root `contracts/` folder, tested by **both** sides: the frontend parses them with the SDK's own `uiMessageChunkSchema`; the backend re-encodes them byte for byte with its Pydantic models | Contract only in prose; JSON Schema | Drift fails CI on whichever side changed; no shared toolchain needed. |
| Products travel as a `data-products` part; tool outputs stay compact | Product list inside the tool output | UI rendering (cards in #20) is decoupled from tool internals. |
| Pre-stream errors are JSON `{error: {code, message, retryAfterSeconds?}}` with 401/429/500; mid-stream errors use the `error` chunk | Errors only inside the stream | Lets the BFF (#10) reject before opening a stream and the UI react per code. |
| Security state (verified orders, failed attempts) is server-side, keyed by chat `id` | Infer from client-sent history | The client controls `messages` and could forge assistant turns. |
| Next.js `/api/chat` with `CHAT_MODE=mock` replays fixtures (`/fixture <name>`) | MSW or a separate mock server | Frontend work (#9) runs before the agent exists, with zero extra tooling. |

**Role of AI.** Claude Code inspected the installed SDK's types and transport code to pin the
exact chunk shapes and request body, wrote the fixtures, and made both test suites validate them.

---

## DL-007 — Embeddings: Gemini instead of Voyage (2026-10-31)

**Supersedes** the embeddings row of DL-002.

| Option | Cost | Limits | Vercel fit | Notes |
|---|---|---|---|---|
| Voyage AI | Requires a payment method to get usable limits (3 RPM without one) | — | HTTP call | Rejected: no card on file for a prototype |
| **Gemini `gemini-embedding-001`** (chosen) | Free tier | 100 RPM, 1,000 RPD, 30K TPM | HTTP call; bundle stays ~13 MB | Multilingual; `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` task types; 768-dim output (Matryoshka truncation) |
| Local model (multilingual-e5-small via ONNX) | Free | None | ~120 MB model + runtime must be bundled; +2–5 s per cold start | Kept as a documented alternative behind the same interface |

**Rationale.** The seed embeds ~90 documents once and query embeddings are cached, so the free
tier is ample. **Known limitation:** on the free tier Google may use submitted content to improve
its products — acceptable for fictional store data, documented in the README; a paid tier or the
local model removes it. CI keeps the deterministic fake embedder (no key).

**Role of AI.** Claude Code compared the three options (limits, bundle size, cold start, privacy);
I chose Gemini.

---

## DL-008 — Store data, quality report and safe seed (2026-10-31, #5, PR A)

**What was built.**
- `python -m etl` validates the CSVs (Pydantic, per-category specs, referential integrity;
  `''` → NULL for optional fields) and applies the DL-002 rules.
- It reloads the store tables in one transaction under an advisory lock (drop and recreate, no
  `CASCADE`).
- It writes `docs/data-quality-report.md`, with 14 anomaly types and a DL-001 traceability table.
- Guards: the target host is printed first; non-local hosts need `--yes`; the fake embedder is
  refused in production; the unpooled Neon URL is used when set.

**Decision.** `not_on_sale_in_order` (column `order_items.product_not_on_sale`) flags products
whose **status** is not `active`: coming soon (never on sale) or discontinued (no longer offered,
so the order item cannot be exchanged for the same product). It does not flag products that are
merely out of stock: `products.is_sellable` is the stock-aware flag, and the two names were made
different on purpose. Order 4 contains
product 96, which is out of stock today; that says nothing about the past order. Only orders 3
and 14 (product 130) are flagged, matching DL-001.

**Decision.** The report is rendered from the in-memory payload, so a CI test can compare it
byte for byte with the committed file without a database.

**Role of AI.** Claude Code implemented the tasks test-first from `tasks.md`. Running the
pipeline on the real data surfaced the order-4 case, and I agreed with the refinement.

---

## DL-009 — Chat web spec (2026-10-31, #9)

Spec Kit artifacts for `specs/003-chat-web` (spec → clarify → plan → tasks → analyze).

| Decision | Alternatives | Rationale |
|---|---|---|
| Full-page chat at `/` | Landing page with a floating widget; both | Fastest path to P0, best on mobile; the evaluator lands in the conversation. A landing page can come with the Figma pass (#18). |
| **Basic product cards in #9** from the contract's `ProductCard` (no image field) | Markdown list now, cards in #20 | Chosen over the contract doc's "markdown in P0" note; #20 keeps branded variants. Cards only format values (constitution I). |
| 401 → `/login?reason=expired` with a placeholder page | Inline notice; redirect to a 404 until #10 | Testable now; #10 replaces the page behind a fixed path and query. |
| Errors mapped by one pure `toChatError()` over the SDK's `APICallError` (`statusCode`, `responseBody`) | Custom `fetch` wrapper | Verified in `ai@7` source that the transport keeps status and body; trivially unit-tested from the `http-*` fixtures. |
| Retry via `regenerate()`; also offered when the 429 countdown ends | `sendMessage` with the same text | Never duplicates the user bubble. |
| **Streamdown** for streaming markdown | `react-markdown` + `remark-gfm`; AI Elements | Closes incomplete markdown mid-stream, sanitizes HTML and hardens links; v2 keeps heavy plugins opt-in. |
| Typed pt-BR catalog, no i18n framework yet | `next-intl` now | YAGNI until the PT/EN switch (#13); the catalog's type is what `en` must satisfy. |
| Component tests drive the real `useChat` with a stub `fetch` serving the fixture files (jsdom + Testing Library) | MSW; Playwright | No network or keys; fixtures stay the single source. Playwright is #16. |

**Spec review (PR #32, QA + senior).** Approved with changes. Applied before implementation:
- Streamdown hardened: its 2.7.1 defaults allow any link/image prefix and `data:` images, so the
  model could exfiltrate PII through an image URL. Images are now blocked, links are
  allow-listed and raw HTML is off.
- `/api/chat` fails closed to `backend` in production when `CHAT_MODE` is unset.
- A dropped stream ends as `ready` in ai@7, so it is detected in `onFinish`.
- Error text from SDK errors is never shown.
- Rapid double-send is guarded.
- Scope cut to 3 implementation PRs.

**Role of AI.** Claude Code drafted the artifacts, asked the clarification questions (decisions
were mine), checked `ai@7`, `@ai-sdk/react@4` and Next 16 behaviour in `node_modules`, and ran
the cross-artifact analysis whose 9 findings (3 medium) were fixed before review.

**Implementation, PR 1 (Foundation + US1).** Findings that changed the plan:
- `rehype-harden` 1.1.8 matches link prefixes by **origin**, so `["https://", "http://", "mailto:"]`
  blocked every real link (and required a `defaultOrigin`). Links now use `["*"]`, which harden
  limits to http(s) and which always blocks `javascript:`, `data:`, `file:` and `vbscript:`. The
  custom `a` renderer re-checks `^(https?:|mailto:)` before rendering an anchor. Images stay
  blocked (`allowedImagePrefixes: []`, `img: () => null`). Blocked items are removed or shown as
  plain text, never harden's English "[blocked]" placeholder with hard-coded grays.
- Streamdown's own link-safety modal is disabled (`linkSafety.enabled: false`); links open in a
  new tab with `rel="noopener noreferrer"`.
- `@source` in `globals.css` is `../../node_modules/streamdown/dist/*.js` (relative to
  `src/app/`), not `../node_modules/…` as written in the tasks. Verified in the built CSS.
- `src/lib/i18n` is split: `index.ts` (server-safe `locale`, `getMessages`, `format`) and
  `context.tsx` (`"use client"` context and `useMessages`), so server pages can read the catalog.
- The chat log is `aria-live="off"`; a separate polite region announces each finished answer once.
- A minimal `ChatError` (retryable notice only) ships in PR 1 for the dropped-stream case; PR 2
  adds the countdown and budget lock.
- Review (QA + senior): `finishReason` is optional in the contract and the backend omits it when
  unset, so `finishReason == null` would flag complete answers as dropped. A small `ChatTransport`
  subclass now records whether the `finish` chunk arrived. Assistant bubbles with no visible part
  (`step-start`, empty text) are hidden so the typing indicator stays until the first content.
- Raw HTML in an answer is shown as escaped text, never parsed (accepted; safe).
- The double-send guard and the dropped-stream detection were mutation-checked: disabling either
  makes its flow test fail.

**Implementation, PR 2 (US2 + US3).**
- Error side effects (401 redirect, rate-limit lock, budget lock) run in `useChat`'s `onError`,
  not in an effect (lint `set-state-in-effect`; `useChat` reads callbacks through a latest ref,
  so there are no stale closures).
- `ChatError` is keyed per error so a repeated rate limit restarts its countdown; starting a
  send also clears the rate-limit lock. The budget lock is separate state that lasts the page
  session and is checked in `run()`.
- `ToolStatus` puts the state suffix in sr-only content (not `aria-label`) so the change is
  announced by its `role="status"` region.

**Implementation, PR 3 (US4 + polish).** `viewport` with `viewportFit: "cover"` and a
safe-area bottom padding on the input bar; page metadata copy moved into the catalog. Audits: no
user-visible literals outside the catalog, no hard-coded colours, no `console.*` with message
content (FR-015/017, SC-005). Production fail-closed checked by hand: `NODE_ENV=production`
without `CHAT_MODE` proxies to the backend (500 "BACKEND_URL is not configured") instead of
replaying fixtures.

## DL-010 — Retrieval and search index (2026-10-31, #5, PR B)

| Decision | Alternatives | Rationale |
|---|---|---|
| Hybrid search = any-term full-text (`pt_unaccent`) + cosine vector, fused with RRF k=60 in one SQL query | AND-semantics `plainto_tsquery`; weighted score sum | OR-ing lexemes keeps recall for natural-language questions; RRF needs no tuning. |
| Long lexemes (6+ chars) match by their first 5 characters (`devol:*`) | Plain stems; hand-written synonyms | The Portuguese stemmer maps *devolver* to `devolv` and *devolução* to `devoluc`, so "posso devolver meu pedido?" never matched §4.1 by full-text. A prefix fixes it without curated keywords. Found by the reference-query test. |
| Fake embedder: hashed 3-5-grams, whole word counted, first line (title) weighted 3x | Plain n-grams | With plain n-grams a long product description diluted the model name ("Yamaha C40" ranked 8th by vector). Title weighting mimics what real models do and keeps the CI criteria meaningful. |
| `embedding_cache` DDL lives in `etl/cache.sql`, run before the embedding step and again inside the seed | Keep it only in `schema.sql` | On a fresh database the cache table must exist before embeddings are computed, and paid vectors are committed separately from the reload. |
| Fake embedder refused for any remote target, not only `ENVIRONMENT=production` | Environment check only | A laptop `.env` says `local` while pointing at Neon (#31 review). |
| Index tables (`policy_chunks`, `product_search_docs`, `index_metadata`) are owned by the seed but excluded from the store-table checksums | Include them | Vectors depend on the provider, so only the store tables are comparable between local and Neon. |

Query-time safety: `search_*` never raises on provider failure; it degrades to full-text with one
warning, and `index_metadata` (provider/model of the index) is read at most every 5 minutes.

**Role of AI.** Claude Code implemented the tasks from the spec; the stemmer gap and the fake
embedder weighting were found by the reference-query tests, not predicted.


## DL-011 — Agent core plan (2026-10-31, #6/#7/#8)

Spec Kit plan, research, data model, contracts and tasks for `specs/002-agent-core`, delivered
as 3 PRs: core (#6, P0), actions (#7, P2), MCP (#8, P2).

| Decision | Alternatives | Rationale |
|---|---|---|
| Route in plain Python, then stream one `langchain.agents.create_agent` (specialist with Haiku, or general with Sonnet) per request | An outer LangGraph graph with router/specialist/general nodes | The senior review showed that nested-agent `custom` and `updates` events only surface with `subgraphs=True`. The router is never streamed, so an outer graph adds nothing. `create_react_agent` is deprecated. |
| Pinned `langgraph 1.2.19`, `langchain 1.4.7`, `langchain-anthropic 1.7.7`, `langchain-core 1.7.3`, imported lazily | A hand-written loop on the `anthropic` SDK | Keeps DL-002. About 46 MB and about 1 s of cold import, mitigated by lazy imports. The hand-written loop stays as the fallback. |
| Tools are plain async functions with an explicit ctx-free schema; the wrapper turns `ToolError` into `ToolException` | `StructuredTool.from_function(partial(...))` | `partial` breaks schema inference, and LangGraph's tool node re-raises unknown exceptions (verified). |
| Verification state in Postgres; attempts reserved atomically; per-conversation lock at 3 plus a per-order 30 min lock at 5 | In memory; per-conversation only | Serverless instances share nothing. A client-chosen chat id would otherwise reset the lockout. |
| Jev first, Haiku fallback, one 2.5 s router budget | Jev with retries; separate timeouts | First token within 3 s (SC-006). A 1 h spike decides the threshold and whether Jev is the default. |
| The fake scenario suite proves tools, wiring and the contract; behaviour is proven with `--live` | Claiming fake mode proves Stories 1–5 | Scripted router and model would only check the script against itself (review). |

**Review (QA + senior).**
- **QA** checked the facts against the CSVs and fixed two scenarios the data cannot support:
  - US3-2 now uses order 4;
  - US3-6 now uses order 10 with customer 43's phone.
- **QA** also realigned the `data-products` order with the #4 contract and pinned the Saturday dates around Finados.
- **Senior** verified three LangGraph API pitfalls in a throwaway venv, plus the lockout bypass. All are applied above.

**Role of AI.** Claude Code drafted the artifacts and ran the research and the two reviews with subagents. The research covered PyPI versions and an offline fake-model loop. The decisions and the 3-PR split were mine.

**Implementation outcome (PR 1, #6).**
- Built as planned: pinned versions as above, no outer graph, per-request `create_agent`, the 8 read tools, `POST /api/chat`, 20 fake-mode scenarios plus 9 `live_only` ones.
- Deviations:
  - `get_order_status` takes an optional `contact` (a verified order needs none), and `reserve_attempt`/`confirm_success` commit on their own, because the pool rolls back a connection when the tool raises right after a failed check (found by the lockout test).
  - Long text-search lexemes were already matched by a 5-character prefix (DL-010), which US1-7 relies on.
  - The US1-7 test searches by words that only exist in the untrusted description: a "Fender Jazz Bass" query legitimately ranks the bass named "Bass" first.
  - The Jev request body (`state` plus a `choice` question) follows the research notes and is unverified until the router spike runs.
- **Residual risk:** until #10 binds the chat id to a user, anyone who knows a chat id sees the orders verified in it. The per-order lock (5 failures, 30 min) still stops guessing across chat ids.
- **Not done here (needs the user's keys):** the router spike (`python -m evals.router_spike`), `python -m evals --live` and the manual end-to-end through the UI.

## DL-012 — Models via OpenRouter (2026-11-01)

**Context.** One key for every model is simpler than Anthropic plus TypeSafe. `LLM_PROVIDER` and `ROUTER_PROVIDER` gained an `openrouter` value; model ids are settings (`SPECIALIST_MODEL`, `GENERAL_MODEL`, `ROUTER_MODEL`).

**Router spike** (34 scenario messages, previous assistant reply passed as context, ~US$0.001 per run):

| Model | Accuracy | p50 / p95 | Confidence |
|---|---|---|---|
| `perplexity/pplx-decider-v1.2` | 30/34 | 456 / 694 ms | spread 0.3–1.0 |
| `deepseek/deepseek-v4.1-flash` | 30/34 | 546 / 984 ms | 28 of 34 at 0.9 |
| `typesafe/jev-1.13` | 23/34 | 395 / 467 ms | spread |

Decision: `perplexity/pplx-decider-v1.2` as the router. Its confidence is the only one the 0.75 threshold can act on.

**Findings.**
- Decider models are not chat models: OpenRouter answers 400 on `/chat/completions` and expects `/api/alpha/decisions` (System One body). The Jev body used before was wrong (`choices` list instead of a `criteria` dict plus `instructions`); fixed.
- DeepSeek is a reasoning model: reasoning tokens ate `max_tokens=200` (`LengthFinishReasonError`, 9/34). The chat router now sends `reasoning: {enabled: false}` and asks only for `intent` and `confidence` (it used to fill `router`, `path` and `model` with invented values).
- The free Gemma id answered 429 on the first call, so it is not usable for the spike or the evals.
- The live eval runner now reuses one client (one event loop); a client per scenario broke the cached provider HTTP client (`Event loop is closed`). Live facts are matched on tool outputs as well as on the answer, and a turn may carry `live_expect` overrides, because a real model picks its own tool arguments.

**Live run** (specialist `openai/gpt-6-luna`, general `deepseek/deepseek-v4.1-flash`): 27/29 and 29/29 on two runs after the prompt fixes. Remaining variance is model nondeterminism, not a defect we found.
- Prompt fixes: greet only in the first message; `get_store_info` only says whether the store is open now, so day-specific hours also need `search_policies`; policy queries are written in Portuguese (the fake embedder is lexical, so English queries missed the hours section).

**Not verified.** Gemini embeddings (cross-language), the direct TypeSafe endpoint, and behaviour under the free tier's rate limits.

**Role of AI.** Claude Code implemented the provider, ran the spike and the live scenarios, and diagnosed the failures. The model choices were the user's.

**Review of PR 1 (QA + senior, 2026-11-01).** No blockers. Applied:
- Router: the primary gets half the budget when a fallback exists (a hung primary used to leave the fallback no time, FR-004).
- `POST /api/chat` rejects chat ids outside `^[A-Za-z0-9_-]{1,128}$` with 400 (they used to fail every order lookup inside the tool).
- History: the window never starts with the assistant, same-role runs are merged, every message (not only the last) is truncated.
- Streams are closed with `aclosing` on disconnect or timeout; the agent schema DDL takes an advisory lock; the pool waits at most 5 s; `order_id` is bounded to int32.
- The system prompt carries the store date and time (FR-018); `mask_pii` also masks a phone without an area code.
- Stricter live assertions: Spanish reply for US5-8, verification request for US3-9, prompt-leak phrases, invented-discount prices.

Not applied, on purpose:
- The per-order failure rows are kept for nonexistent orders too: skipping them would make a lock reveal that an order exists (FR-014). The conversation-id reset and the per-order denial of service stay the documented residual risk of DL-011 until #10.
- Open nits: close text and step parts on a mid-stream error, a request body size cap, and treating `cancellation_reason` as untrusted text. Tracked for #10.
- QA gaps still without a scenario: Saturday 13:01 closing, the shared e-mail between customers 11 and 43 (US3-6), per-order lock (US3-4) and the two-WhatsApp trap through the policy path.

## DL-013 — Actions: returns, complaints, handoff (#7, 2026-11-01)

**Decision.** `check_return_eligibility` (read-only) and `request_return`, `register_complaint`, `handoff_to_human` (writes) on top of the read tools. Eligibility lives in `app/policies/returns.py`, a pure function: §4.1 and §4.3 count 7 calendar days from `estimated_delivery`, §4.2 30 days from `order_date`, then §8.1 90 days from delivery, then the manufacturer warranty with the store's intermediation. Dates are inclusive: day 7 is eligible, day 8 is not.

| Choice | Why |
|---|---|
| A write needs the order verified in this conversation, `confirmed_by_customer is True`, and (returns) an `eligible` decision computed again inside the tool | The prompt asks for an explicit request, the tool does not trust it (FR-020). A refused call writes nothing. |
| `request_return` takes `bought_online` | The #4 contract has no such input, but §4.1 only applies to online purchases, so a regret return could never be requested without it. |
| Orders not yet delivered (pending or confirmed, or no delivery date) are `not_delivered_yet` | The windows start at receipt. |
| `reason` is masked with `mask_pii` and cut at 1000 characters before it is stored | FR-024; the free text is the customer's words. |
| Eval scenarios with a scripted clock (`now:`) are `fake_only`; US6-8 also has a `live_only` variant | The live runs use the real date, at which every dataset order is outside every window (US6-5). |

**Limits.** §4.4 is detected only for a "boquilha" item name: custom setups and "venda final" are not marked in the dataset, and no product in it is a mouthpiece, so US6-4 is covered by a unit test only. A live model asked to open a return for order 4 correctly refused (window ended 2025-12-29) and offered the defect path.

**Role of AI.** Claude Code wrote the rule function, the tools, the scenarios and the tests; the windows and the write guards follow the spec and the manual.

## DL-DOCS-001 — 004 spec, plan and tasks: auth, limits, deploy (#10, 2026-11-01)

**Context.** Two independent spec drafts existed for #10: one on this branch, one on
`docs/10-auth-limits-spec`. The two were compared and merged rather than picking one outright.

**Decision.** This branch's spec/plan/tasks are the ones kept. Folded in from the other draft:
closing the conversation-id residual risk from DL-012 as its own user story (FR-009a: conversation
state is scoped to `(account, conversation_id)`, not the conversation id alone), a sign-in lockout
(5 failed attempts / 15 minutes per username), and exact alignment of the 401/429 error bodies with
the already-shipped `#4` contract (`unauthorized`/`rate_limited`/`budget_exhausted`,
`retryAfterSeconds`) instead of inventing a new shape.

| Choice | Why |
|---|---|
| Auth.js v5, Credentials provider, JWT session strategy | No OAuth/sign-up needed; avoids the full adapter schema a database-session strategy would require for one provider and a handful of accounts. |
| `users`/`login_attempts` owned by the frontend (Node, plain `pg`), not the backend | Only the frontend ever reads/writes them (login path, create-user CLI); the backend only verifies an opaque, already-issued JWT and never touches a password. |
| `rate_limit_minute`/`token_usage_daily` owned by the backend, same idempotent `CREATE TABLE IF NOT EXISTS` + advisory-lock pattern as the existing `conversation_state` | Both are read and written only by the backend; matches the project's existing schema convention instead of introducing a numbered-migrations mechanism. |
| Fixed-window (not sliding-window/token-bucket) rate limiting | A single-digit number of accounts does not need a distributed limiter; the realistic adversary at this scale is a runaway client/bug, not a sophisticated rate-limit evader (documented trade-off, not an oversight). |
| Service JWT: HS256, 120s lifetime, 30s clock-skew leeway | Short-lived per the backlog decision; the skew leeway avoids false-positive rejections from ordinary VM clock drift at this token lifetime. |

**Role of AI.** Claude Code wrote both the compared drafts' synthesis and the spec/plan/tasks
themselves; the merge decisions (which story to add, which numbers to keep) were made against the
existing decision log and contract, not invented.

## DL-BE-001 — Service JWT, conversation scoping, rate limit and budget (#10, 2026-11-01)

**Decision.** `app/auth` (service JWT verify + the `require_service_account` FastAPI dependency)
and `app/limits` (rate limit + daily budget, Postgres-backed) gate `POST /api/chat`. The dependency
fails closed: a missing `SERVICE_JWT_SECRET` is a `500`, never treated as "accept any token". A
startup check (`app/main.py: check_fail_closed_config`) additionally refuses to come up in
`Environment.PRODUCTION` if `SERVICE_JWT_SECRET`, `DATABASE_URL`, or the configured LLM provider's
key is missing.

**`conversation_state` is now keyed by `(user_id, conversation_id)`**, not `conversation_id` alone
— this closes the residual risk DL-012 flagged ("until #10 binds the chat id to a user, anyone who
knows a chat id sees the orders verified in it"). `ToolContext` carries `user_id`; every call into
`app.agent.state` (`get`, `reserve_attempt`, `confirm_success`) now requires it. A unit test
(`tests/agent/test_state.py::test_a_conversation_id_alone_does_not_grant_access_across_accounts`)
and a full-request test through `POST /api/chat` (`tests/api/test_chat_auth_and_limits.py`) both
cover it.

**Limits.** 20 requests/minute (fixed window, UTC-minute bucket) and 200,000 input+output
tokens/day (local day in `America/Campo_Grande`, computed with `zoneinfo`) per account, checked
before the agent runs (rate first, then budget — cheaper and more common first) and recorded after
the turn finishes from its actual token counts. A turn already streaming when a limit is reached
elsewhere is unaffected; only the next request is refused. Both refusals reuse the existing `#4`
chat-stream error contract exactly (`rate_limited`/`budget_exhausted`, `retryAfterSeconds`,
`Retry-After` header).

**Found by the new tests, fixed before merge:** the fail-closed startup check had a logic bug that
flagged the (deliberately keyless) fake LLM provider as a missing-config error in production;
`tests/test_fail_closed_startup.py` caught it immediately.

**Not done here.** Numbered-migration tooling was deliberately not introduced; new tables use the
project's existing idempotent-DDL-on-first-use pattern. The Anthropic/OpenRouter workspace spend
cap is a dashboard setting, documented in `quickstart.md`, not enforced in code (FR-016).

**Role of AI.** Claude Code implemented the dependency, the schema changes, the limiter, the tests,
and found/fixed the startup-check bug the tests surfaced.

## DL-FE-001 — Auth.js login and create-user CLI (#10, 2026-11-01)

**Decision.** Auth.js v5 (Credentials provider, JWT sessions, 30-day max age) replaces the
`/login` placeholder. `src/proxy.ts` (Next.js 16 renamed "middleware" to "proxy"; with a `src/`
layout the file must live at `src/proxy.ts`, next to `app/`, or it is silently never loaded —
cost real debugging time) redirects an unauthenticated request to `/login`, accepting `callbackUrl`
only as a same-site relative path. `scripts/create-user.ts` is the only way an account is created;
there is no sign-up page or endpoint. A sign-in lockout (5 failures/15 minutes per username) is
checked before the password comparison. `POST /api/chat`'s route handler requires a session,
re-checks the account is not disabled at mint time (not only at login), and mints a 120s HS256
service JWT forwarded to the backend as `Authorization: Bearer`.

**Verified end to end locally** (not just unit tests): an unauthenticated request to `/` redirects
to `/login`; logging in via the Auth.js credentials callback sets a session cookie; an authenticated
`POST /api/chat` reaches the backend past `require_service_account` (confirmed via the backend
log, not just a 200 status).

**Role of AI.** Claude Code implemented the login flow, the CLI, the proxy, and diagnosed the
Next.js 16 proxy/middleware rename that was silently breaking redirects in manual testing.

