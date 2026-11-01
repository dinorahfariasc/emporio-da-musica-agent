# Contract: `POST /api/chat` (backend)

Implements the chat stream contract (`docs/contracts/chat-stream.md`, #4) without changing it. The
request and chunk models already exist in `backend/app/chat/protocol.py`.

## Request

`ChatRequest {id, messages[], trigger, messageId?}`.

- **Request `id`**: the conversation id. It is the key for `conversation_state`. Binding it to the
  authenticated user is #10's job.
- **History**: the agent uses `messages[-HISTORY_MAX_MESSAGES:]`, text parts only, for context.
  It never takes security state from them.
- **Latest user text**: truncated to `INPUT_MAX_CHARS`. When it is empty or whitespace, the agent
  sends a short helpful reply and calls no LLM tool.
- **`trigger: "regenerate-message"`**: the last user message is answered again.

## Response

`text/event-stream` with `x-vercel-ai-ui-message-stream: v1`. Each answer gets a **new**
`messageId`; repeating one hides the answer in the UI (a bug found in #9).

Chunk order for one turn:

```
start
  [start-step  tool-input-available*  (data-products)*  tool-output-available|tool-output-error*  finish-step]*
  start-step  text-start  text-delta+  text-end  finish-step
message-metadata {route:{intent,confidence,router}, model, usage:{inputTokens,outputTokens}}
finish {finishReason: "stop" | "length" | "tool-calls"}
[DONE]
```

The router's own model call is never streamed.

## Errors

| Situation | Behaviour |
|---|---|
| Invalid body | HTTP 400 `invalid_request`, an `ErrorResponse` (#4) |
| LLM provider error, timeout, recursion limit (`AGENT_MAX_STEPS`), turn timeout | Mid-stream `error` chunk with a pt-BR or EN catalog message (in the customer's language when known), then `[DONE]`. Never the exception text. |
| Tool failure | `tool-output-error` with a stable code (`verification_failed`, `not_found`, `locked`, `unavailable`). The model then explains the situation in words. |
| Router failure | Fallback router; if both fail, `intent=unclear, confidence=0`, then the general path |

401 and 429 responses (auth, rate limit, budget) are produced upstream by #10, not here.

## Tool names (exactly the 11 contract names; UI labels live in the frontend catalog)

- `search_products`
- `get_product`
- `find_similar_products`
- `get_active_promotions`
- `calculate_payment_options`
- `get_order_status`
- `search_policies`
- `get_store_info`
- `request_return` (#7)
- `register_complaint` (#7)
- `handoff_to_human` (#7)

`check_return_eligibility` (#7) is new and is not in the #4 contract table. The UI shows the
fallback label "Consultando…" for it. When #7 lands, its pt-BR label is added to the contract and
the frontend catalog.
