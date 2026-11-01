# Research: Agent core (002)

Versions were checked on 2026-10-31 against PyPI and installed source in a throwaway Python 3.13
venv, not training data. A fake-model ReAct loop was run offline to prove the test approach.

## R1 — Orchestration: LangGraph outer graph, `create_agent` for the general path

- **Decision**:
  - LangGraph builds the outer graph: `route → specialized node | general agent`, chosen by a
    conditional edge.
  - The general path uses `langchain.agents.create_agent(model, tools, system_prompt=…)`, which
    returns a compiled graph with nodes `model` and `tools`.
  - Each specialized node is also a `create_agent` with a small tool list and Haiku.
  - Pin exact versions: `langgraph==1.2.19`, `langchain==1.4.7`, `langchain-anthropic==1.7.7`,
    `langchain-core==1.7.3`; `anthropic` 2.3.0 comes in transitively.
- **Rationale**:
  - The architecture is already decided (DL-002).
  - LangGraph gives the typed routing graph, `recursion_limit` and `get_stream_writer`, which
    match the plan directly.
  - The stack is about 46 MB; a warm import takes about 1.1 s.
- **Findings / gotchas**:
  - `langgraph.prebuilt.create_react_agent` is deprecated in favour of
    `langchain.agents.create_agent`.
  - With `ChatAnthropic`, `AIMessageChunk.content` can be a list of blocks. Read `chunk.text`.
  - Exceeding `recursion_limit` raises `GraphRecursionError`. It is mapped to a friendly
    `error` chunk (FR-027).
  - Import LangGraph and langchain lazily inside the chat handler, so `/api/health` cold starts
    stay fast.
- **Alternatives**: a hand-written loop on the `anthropic` SDK. It is about 100 lines, starts
  faster and is simpler to fake. It stays the fallback inside the graph nodes if the adapter
  becomes painful.

## R2 — Streaming adapter: LangGraph → AI SDK v1 UI message stream

- **Decision**: one adapter, `app/agent/stream.py`, consumes
  `graph.astream(inputs, stream_mode=["messages", "updates", "custom"],
  config={"recursion_limit": N})` and emits the contract chunks from `app/chat/protocol.py`:

  | LangGraph event | Contract chunk |
  |---|---|
  | first event | `start` (new `messageId` per answer) |
  | `updates` from `model` with complete `tool_calls` | `start-step`, then `tool-input-available` per call |
  | `messages`: `ToolMessage` | `tool-output-available`, or `tool-output-error` with a stable error code when `status == "error"` |
  | `custom`: `{"type": "data-products", …}` | `data-products` |
  | `messages`: text chunks from the answering model | `text-start` / `text-delta` / `text-end`, opened on the first chunk of a message id |
  | end of each model step | `finish-step` |
  | end of the run | `message-metadata` (route, model, usage), then `finish` with `finishReason` |
  | exception, timeout or recursion limit | `error` with a catalog message (never the exception text) |

- **Rationale**:
  - `astream_events(v2)` is noisier and slower.
  - The three stream modes carry everything the contract needs.
  - Tool inputs are read from the complete `AIMessage` in `updates`, because the fragments in
    `messages` are partial JSON.
- **Tool outputs**: they are compact summaries such as `{"count": 2, "productIds": [91, 87]}`,
  never personal data. The UI never renders them (003), but they are logged.
- **Router chunks**: the router's own model call (Haiku fallback) is filtered out of `messages`
  by `meta["langgraph_node"]`, so it never streams to the customer.

## R3 — Router: Jev first, Haiku structured output as fallback

- **Jev (TypeSafe AI)**:
  - HTTP call: `POST https://api.typesafe.ai/v1/systemone` with a Bearer key, model
    `jev-latest`.
  - Request: `state` (the latest message plus short context) and a `choice` question whose
    labels are the intents of FR-001.
  - Response: `answers.intent.{choice, confidence, probabilities}`.
  - Claimed latency is 70–500 ms. There is no official Python SDK, so a plain `httpx` client is
    used (10 s timeout, retry on 429/529).
- **Spike, time-boxed to 1 h (task)**: validate
  - (a) the key and credit;
  - (b) p50 and p95 latency;
  - (c) accuracy on the reference messages, PT and EN, against Haiku;
  - (d) confidence calibration, to pick `ROUTER_CONFIDENCE_THRESHOLD`;
  - (e) 429 behaviour.

  If Jev fails the spike, `ROUTER_PROVIDER=haiku` becomes the production default. The
  comparison goes into the README.
- **Fallback**:

  ```python
  ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0, max_tokens=200)
      .with_structured_output(Route, include_raw=True)
  ```

  The default method is `function_calling` (a forced tool call). A parse failure gives
  `intent="unclear", confidence=0`, which goes to the general path.
- **Provider order**: `ROUTER_PROVIDER` picks the primary (`jev` | `haiku` | `fake`). On error or
  timeout (`ROUTER_TIMEOUT_MS`, default 1500), Haiku takes over (FR-004). The metadata `router`
  field records which one answered.
- **Context**: the router sees only the latest customer message plus the previous assistant
  turn, which keeps it cheap. Multi-intent detection is part of the label set.

## R4 — Models and limits (configurable, FR-003, FR-027)

| Setting | Default |
|---|---|
| `SPECIALIST_MODEL` | `claude-haiku-4-5-20251001` |
| `GENERAL_MODEL` | `claude-sonnet-5-5` |
| `ROUTER_CONFIDENCE_THRESHOLD` | 0.75 (tuned by the spike) |
| `AGENT_MAX_STEPS` | 8 tool rounds, mapped to `recursion_limit = 2 * steps + 2` |
| `LLM_MAX_TOKENS` | 1024 |
| `LLM_TIMEOUT_S` | 30 |
| `TURN_TIMEOUT_S` | 60 (whole turn, `asyncio.timeout`) |
| `HISTORY_MAX_MESSAGES` | 12 (most recent; FR edge case "very long conversations") |
| `INPUT_MAX_CHARS` | 2000 (the UI limit), truncated server-side |

`ChatAnthropic(..., max_tokens=…, default_request_timeout=…, max_retries=1, streaming=True)`.

## R5 — Tools: plain async Python functions, shared by the agent and MCP

- **Decision**:
  - The tools are plain `async def` functions in `app/tools/`, with typed `Annotated` arguments
    and docstrings. Each takes an explicit `ToolContext` (DB pool, embedder, conversation id,
    clock), so no globals are needed.
  - They return Pydantic models. Facts are computed only here, from `app/catalog/rules.py` and a
    new `app/policies/rules.py` (constitution I).
  - The agent wraps them with `StructuredTool.from_function(coroutine=…)`, binding the context
    with `functools.partial`. MCP registers the same functions in #8.
- **Products data part**: tools that return products call `get_stream_writer()` with a
  `data-products` payload built by one mapper. The mapper follows the 001 contract for
  `ProductCard`.
- **Untrusted descriptions**: products 135–144 hide their contradictory descriptions through
  `display_description()` (DL-002 rule).
- **Retrieved policy text**: it is wrapped as quoted data in the tool result and the system
  prompt says it is reference material, not instructions (FR-023).

## R6 — Conversation and verification state on serverless

- **Finding**: Vercel Fluid compute runs many instances and recycles them, so in-memory state
  would lose or bypass the lockout.
- **Decision**: a Postgres table `conversation_state` (see data-model).
  - The verification tool reads the row and changes it in one atomic statement: `UPDATE …
    RETURNING`, or `INSERT … ON CONFLICT`.
  - The tool never trusts a "verified" flag in the client's message history (FR-016).
  - The conversation id is the contract `id`. Binding it to the authenticated user is #10's job;
    it is noted in the contract.
- **History**: comes from the request's `messages` (the client sends the history, as in the
  contract). Security state never comes from there.

## R7 — Time, opening hours and holidays

- `zoneinfo("America/Campo_Grande")`. A `Clock` protocol is injected so tests can control "now".
- Opening hours come from §2 of the manual, encoded in `app/policies/hours.py` with the table in
  code. National holidays are a fixed list for 2026–2027 (the spec's assumption).
- `get_store_info` returns `is_open_now` and `next_opening` deterministically. The LLM only
  phrases them.

## R8 — Payment options (FR-006)

`calculate_payment_options(product_id | amount)` in `app/policies/payments.py` computes, using
`Decimal` and `ROUND_HALF_UP`:

- **PIX**: 5% off the list price. It is not applied when a promotion is active; the result
  carries `pix_applies=False` and a reason.
- **Installments (§3.1)**:
  - up to 3x: no minimum, except that purchases below R$ 50 are not split;
  - 4–6x: each installment at least R$ 80;
  - 7–12x: each installment at least R$ 100.
- **Combined payment**: only when the amount is above R$ 2.000.

## R9 — Testing without paid services (constitution IV, FR-029)

- **Fake models**: `FakeToolModel`, a `GenericFakeChatModel` subclass with `bind_tools` and
  streamed `tool_call_chunks` (proven offline). The stock fake cannot stream tool calls.
- **Other fakes**: `FakeRouter` returns a scripted `Route`, and the fake embedder already exists.
  Tests use the local Postgres from docker compose.
- **Layers**:
  1. Unit tests for the rules: payments, hours, verification, eligibility.
  2. Tool tests against the seeded DB.
  3. Adapter tests: a scripted graph run must produce chunks that validate against the contract
     schema, using the same check as the frontend contract test.
  4. A **scenario suite** in `backend/evals/scenarios/*.yaml`. Each scenario holds the messages
     and asserts the route, the tools called, the required facts and the forbidden facts. It runs
     in fake mode in CI. With `--live` it runs against real models and exports transcripts for
     the README (#11).

## R10 — MCP (P2, #8), noted for later

- **Versions**: `fastmcp` 4.1.4 (the official SDK `mcp` is 2.3.0).
- **Mounting**:
  - `mcp.http_app(path="/", stateless_http=True, json_response=True)`, mounted at `/mcp`.
  - The FastAPI lifespan must be combined with the MCP app's lifespan.
- **Auth**: a small ASGI middleware compares the Bearer token with `MCP_API_KEY` using
  `hmac.compare_digest`.
- **Tools**: the same functions from `app/tools`.
- **Open risk**: whether Vercel buffers SSE on this route. `json_response=True` avoids it; a smoke
  test after deploy checks it.

## R11 — Vercel runtime

- The Python runtime supports streaming `StreamingResponse`, with a maximum duration of 300 s on
  Hobby. The bundle limit is 500 MB, and the new dependencies add about 50 MB.
- Python 3.13 is pinned.
- Cold-start cost is reduced with lazy imports (R1).
