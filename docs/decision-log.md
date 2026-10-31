# Decision Log

Living record of how this project's decisions were made, which alternatives were considered,
and how AI assistants took part in the process. Updated throughout development; the README
summarizes it and links here.

**Entry format:** context → decision → alternatives → rationale → role of AI.

---

## DL-001 — Kickoff: reading the brief and the data (2026-10-31)

**Context.** Artefact technical challenge (AI Engineer): a customer-service agent for the
fictional store Empório da Música, backed by operational CSVs and a policies manual (PDF).
Deadline: P0 done by 2026-11-01 evening; 2026-11-02 reserved for improvements.

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
