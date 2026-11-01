# Implementation Plan: Agent core (Melody)

**Branch**: `docs/6-agent-core-plan` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-agent-core/spec.md` (issue #6; US6 = #7, US7 = #8)

## Summary

Melody's backend is `POST /api/chat` on the existing FastAPI app. It streams the #4 contract from
a LangGraph graph:

- A typed **router** (Jev, with Haiku structured output as fallback) classifies each message.
- High-confidence single intents go to a **specialist** (Haiku with a small tool set).
- Everything else goes to a **general agent** (Sonnet with every tool).
- All facts (prices, PIX, installments, availability, orders, hours, eligibility) come from
  deterministic async **tools** over the 001 data and retrieval.
- Order verification state lives in Postgres.
- A fake-model **scenario suite** proves Stories 1–5 offline.

Delivered as 3 PRs: core (#6), actions (#7), MCP (#8).

## Technical Context

**Language/Version**: Python 3.13 (uv)

**Primary Dependencies**:

- existing: FastAPI, psycopg 3 + pool, pydantic, httpx;
- new, pinned: `langgraph==1.2.19`, `langchain==1.4.7`, `langchain-anthropic==1.7.7`,
  `langchain-core==1.7.3`, and `pyyaml` for the scenarios;
- #8: `fastmcp==4.1.4`.

**Storage**: Postgres 16 + pgvector (Neon in production, docker compose locally). New tables:
`conversation_state`, plus `service_requests` for #7.

**Testing**:

- pytest + pytest-asyncio against the local DB;
- `FakeToolModel` and `FakeRouter`;
- a YAML scenario suite that runs with fakes in CI and with `--live` on demand.

**Target Platform**: Vercel Python functions (Fluid compute, private service behind Next.js).

**Project Type**: web service (the backend of the existing web app).

**Performance Goals**: first token in 3 s or less and a typical answer in 10 s or less in
production, warm (SC-006). The router adds less than 500 ms when Jev is used.

**Constraints**:

- every fact deterministic;
- no paid calls in CI;
- 300 s maximum function duration;
- the turn is bounded by steps, tokens and timeout (R4);
- personal data masked in logs;
- lazy imports for cold start.

**Scale/Scope**: a demo with low traffic; 144 products, 50 orders, about 40 policy chunks; 11 + 1
tools.

## Constitution Check

| Principle | How the plan complies |
|---|---|
| I. Facts from the system | Prices, PIX, installments, availability, orders, hours and eligibility are computed in `app/catalog/rules.py`, `app/policies/*.py` and the tools, with parameterized SQL only. The LLM gets results and phrases them. There is no text-to-SQL. A missing fact is reported as `not_found`, and alternatives are offered. ✅ |
| II. LLM only where it adds value | A Jev router decides first. High-confidence intents go to Haiku specialists; Sonnet is used only for low confidence, multi-intent or unclear messages. The route, model and tokens are logged per turn. ✅ |
| III. Clean, traceable data | The plan reuses the 001 ETL outputs and makes no new data corrections. Input text is normalized with `nfc()`. ✅ |
| IV. Tested before done | Unit tests for every rule and tool, adapter tests against the contract schema, and a fake-mode scenario suite in CI. The README conversations come from `--live` runs. ✅ |
| V. Safe and respectful | Verification state is server-side in Postgres, with a lockout after 3 failures and one generic failure message. `mask_pii` is applied in logs. Retrieved text is marked as reference, not instructions. Write tools need an explicit request plus `confirmed_by_customer`. Accessories and other out-of-scope requests are declined. Auth, budget and rate limit are enforced upstream (#10). ✅ |
| VI. Simple, modular, replaceable | Router, LLM and embeddings sit behind providers selected by settings. Tools are plain functions reused by MCP, and the MCP layer holds no logic. LangGraph is used only for the outer graph (justified below). ✅ |

**Gate**: PASS. Re-checked after Phase 1: no new violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-agent-core/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/chat-endpoint.md, contracts/tools.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code

```text
backend/
├── app/
│   ├── api/chat.py              # POST /api/chat → StreamingResponse (lazy-imports the agent)
│   ├── agent/
│   │   ├── schema.sql           # conversation_state, service_requests
│   │   ├── graph.py             # router node → conditional edge → specialist | general
│   │   ├── router.py            # Router protocol; JevRouter, HaikuRouter, FakeRouter; fallback chain
│   │   ├── models.py            # chat model factory (Anthropic | Fake) from settings
│   │   ├── prompts.py           # Melody persona (§7.1/§7.2), safety rules, per-intent instructions
│   │   ├── stream.py            # LangGraph astream → contract chunks (R2)
│   │   ├── state.py             # conversation_state access (atomic verification updates)
│   │   ├── logging.py           # turn log + mask_pii
│   │   └── fakes.py             # FakeToolModel, FakeRouter (also used by evals)
│   ├── tools/
│   │   ├── context.py           # ToolContext, ToolError, Clock
│   │   ├── products.py          # search_products, get_product, find_similar_products, get_active_promotions
│   │   ├── payments.py          # calculate_payment_options
│   │   ├── orders.py            # get_order_status (+ verification)
│   │   ├── policies.py          # search_policies, get_store_info
│   │   ├── actions.py           # #7: check_return_eligibility, request_return, register_complaint, handoff_to_human
│   │   └── registry.py          # tool list per intent; LangChain wrapping
│   ├── policies/                # pure rules: payments.py, hours.py (+ holidays), returns.py (#7)
│   └── mcp.py                   # #8: FastMCP server + bearer middleware, mounted at /mcp
├── evals/
│   ├── __main__.py              # runner: fake (default) | --live, --export
│   ├── scenarios/*.yaml         # one file per story; route/tools/required/forbidden assertions
│   └── router_spike.py          # Jev vs Haiku latency/accuracy report
└── tests/agent/, tests/tools/, tests/policies/, tests/evals/
```

**Structure Decision**:

- The plan extends the flat `backend/app` package that 001 established.
- Rules (`app/policies`) are pure and synchronous.
- Tools (`app/tools`) are async and touch the DB.
- The agent wiring (`app/agent`) is the only place that imports LangGraph or langchain.

## Delivery (3 PRs)

1. **PR 1 — #6 core (P0)**, Stories 1–5:
   - rules and read tools;
   - `conversation_state`;
   - router with fallback;
   - graph, adapter and `/api/chat`;
   - turn logging;
   - the fake scenario suite;
   - the Jev spike report.

   Production switch: Vercel `CHAT_MODE=backend` plus the API keys, done by the user.
2. **PR 2 — #7 actions (P2)**: returns rules, `service_requests`, the 4 action tools,
   Story 6 scenarios, and the frontend label for `check_return_eligibility`.
3. **PR 3 — #8 MCP (P2)**: FastMCP mount, bearer auth, tests, Vercel rewrite for `/mcp`, and the
   README section.

## Complexity Tracking

| Addition | Why needed | Simpler alternative rejected because |
|---|---|---|
| LangGraph + langchain (about 46 MB, about 1 s cold import) | Router → specialist/general graph, step limits and custom stream events; a project decision (DL-002) and named in the job description | A hand-written `anthropic` loop is simpler and is kept as the fallback inside nodes (R1). The cold-start cost is mitigated with lazy imports. |
| `conversation_state` table | Lockout and per-order verification must survive serverless instance changes (R6) | In-memory state would lose or bypass the lockout; trusting client history violates FR-016 |
| Two router providers | FR-004 requires a fallback; Jev is unproven (spike) | Haiku alone works, but loses the cost/latency demonstration of constitution II |
