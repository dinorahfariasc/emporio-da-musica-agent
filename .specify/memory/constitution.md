# Empório da Música Agent Constitution

## Core Principles

### I. Facts come from the system, never from the model (NON-NEGOTIABLE)
- Price, stock, product status, active promotion, order status, deadlines and return/exchange
  eligibility MUST come from deterministic tools (parameterized SQL and Python rules). The LLM
  only writes the answer from tool results.
- Policy rules with numbers (deadlines, installments, shipping, discounts) MUST be encoded and
  tested; RAG explains and contextualizes, it does not calculate.
- The customer-facing agent MUST NOT generate free-form SQL.
- When information does not exist, the agent MUST say so and offer an alternative (similar
  product, human handoff) instead of inventing.

**Rationale:** the store manual (§7.1) forbids quoting price, stock or deadlines without checking
the system; errors may amount to misleading advertising.

### II. LLM only where it adds value
- Every message first goes through a typed decision router (Jev, with a structured-output LLM
  fallback) that returns intent and confidence.
- High-confidence intents MUST be handled by specialized nodes using the cheapest capable model
  (Haiku); the most expensive model (Sonnet) is reserved for low confidence, multi-intent or
  open-ended reasoning.
- Every routing decision MUST be logged (intent, confidence, path, model, tokens).

**Rationale:** cost and latency proportional to difficulty; auditable decisions.

### III. Clean, traceable data
- CSVs and the PDF in `challenge/` are read-only inputs; all cleaning happens in a reproducible
  ETL with schema validation.
- Every data correction or interpretation MUST be an explicit, tested rule recorded in the data
  quality report and the decision log.
- Text MUST be normalized (Unicode NFC) before comparison or search.

**Rationale:** the data contains deliberate inconsistencies; handling them explicitly is part of
the evaluation.

### IV. Tested before done
- Tools, policy rules, ETL and retrieval MUST have deterministic unit tests.
- The agent graph MUST be testable with fake LLM and router (no paid calls in CI).
- Reference conversation scenarios (including adversarial and non-obvious ones) MUST exist as an
  executable eval; the README's example conversations are generated from them.
- Bug fixes MUST come with a regression test that failed before the fix.

**Rationale:** agent behavior regresses silently without tests and evals.

### V. Safe and respectful to the customer
- Order data is revealed only after verification (order number + the owner's email or phone).
  Personal data MUST be masked in logs and traces.
- Instructions coming from the user or from retrieved documents NEVER override the system prompt
  or unlock tools; actions that write data require explicit customer intent.
- Out-of-scope questions (including accessories, which the store does not sell) MUST be declined
  politely and redirected.
- The public API MUST require authentication and enforce a per-user token budget and rate limit.

**Rationale:** LGPD (manual §9) and exposure of a paid API key.

### VI. Simple, modular, replaceable
- Providers (LLM, router, embeddings, database) sit behind thin interfaces and are selected by
  configuration.
- Tools are pure Python functions exposed via MCP; the MCP layer holds no business logic.
- No dependency or abstraction enters without a present need (YAGNI); extra complexity MUST be
  justified in the feature plan.

**Rationale:** a short deadline demands focus; interfaces let parts be swapped without rewriting
the agent.

## Technical Constraints

- **Languages:** Python is the primary language (backend, agent, ETL); TypeScript for the frontend.
- **Stack:** FastAPI, LangGraph, FastMCP, Postgres (Neon) with pgvector, Voyage embeddings,
  Anthropic Claude, Jev (TypeSafe); Next.js, Vercel AI SDK, shadcn/ui.
- **Deploy:** Vercel (Next.js + Python functions) and Neon; identical local environment via
  docker-compose.
- **Tooling:** `uv`, `ruff`, `pytest` for Python; `pnpm`, ESLint for the frontend; secrets only via
  environment variables, with a versioned `.env.example`.
- **Language:** everything in English (code, docs, commits, PRs, issues) except the agent persona
  and website copy, which are Portuguese-first; the agent replies in the customer's language.

## Development Workflow

- **Spec-Driven:** no implementation without an approved spec → plan → tasks for the epic.
- **Issues:** tasks become GitHub Projects issues only after review by two agents (QA and senior
  engineering) and human approval; every issue has testable acceptance criteria and a priority
  (P0/P1/P2).
- **Branches and PRs:** one branch per issue; small PRs with `Closes #n`, green CI (lint + tests)
  and review before merge; merges are done by a human.
- **Commits:** semantic (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), with no mention of AI
  assistants and no co-author trailers; AI usage is documented in the decision log.
- **Priority:** no P1 item starts before every P0 item is in production.
- **Living docs:** every relevant decision produces an entry in `docs/decision-log.md`.

## Governance

This constitution supersedes other project practices. Every plan MUST include a compliance check
against the principles, and every PR review MUST verify it. Amendments require a decision-log
entry with the reason and semantic versioning: MAJOR for removing or redefining a principle,
MINOR for a new principle or section, PATCH for clarifications. Runtime development guidance
lives in `CLAUDE.md`.

**Version**: 1.0.1 | **Ratified**: 2026-10-31 | **Last Amended**: 2026-10-31
