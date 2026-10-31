# Chat stream contract (backend ⇄ frontend)

The chat speaks the **Vercel AI SDK UI message stream protocol, v1** (verified against `ai@7`).
This document fixes the subset we use so the frontend (#9) and the agent (#6) can be built in
parallel. Machine-checked fixtures live in [`contracts/chat-stream/fixtures/`](../../contracts/chat-stream/fixtures/).

```
browser ──useChat──▶ Next.js POST /api/chat (BFF: auth, limits — #10) ──binding──▶ FastAPI POST /api/chat
```

`CHAT_MODE=mock` makes the Next.js route replay the fixtures (send `/fixture <name>` in a
message to pick one); `CHAT_MODE=backend` proxies to FastAPI.

## Request

`POST /api/chat`, JSON — the AI SDK `DefaultChatTransport` body (see `request-submit.json`):

| Field | Type | Notes |
|---|---|---|
| `id` | string | Chat (thread) id, stable for the whole conversation |
| `messages` | `UIMessage[]` | Full history; each `{id, role, parts}`; the agent reads `text` parts |
| `trigger` | `"submit-message" \| "regenerate-message"` | |
| `messageId` | string? | Present on regenerate |

**Trust boundary.** Client-sent history is conversational context only. Security state — which
orders were verified, failed verification attempts — is kept **server-side keyed by `id`** and is
never inferred from `messages` (a client could forge assistant turns).

## Response (success)

`200`, headers: `Content-Type: text/event-stream`, `x-vercel-ai-ui-message-stream: v1`,
`Cache-Control: no-cache`. Body: SSE events `data: <json>\n\n`, terminated by `data: [DONE]\n\n`.

Chunk order for one assistant turn:

```
start → (start-step → [tool-input-available → tool-output-available|tool-output-error]* → [data-products]? → [text-start → text-delta+ → text-end]? → finish-step)+ → message-metadata → finish → [DONE]
```

| Chunk | Shape | Use |
|---|---|---|
| `start` | `{messageId}` | New assistant message |
| `start-step` / `finish-step` | `{}` | One agent step (tool round or answer) |
| `tool-input-available` | `{toolCallId, toolName, input}` | Tool started; UI shows a status label |
| `tool-output-available` | `{toolCallId, output}` | Tool finished (output is compact; full results go in data parts) |
| `tool-output-error` | `{toolCallId, errorText}` | Tool failed; `errorText` is a code, not user copy |
| `data-products` | `{id, data: {products: ProductCard[]}}` | Products to render as basic cards (#9; branded variants in #20). The answer text should summarize or recommend, not relist every product already in the cards (note for the agent prompt, #6) |
| `text-start` / `text-delta` / `text-end` | `{id, delta?}` | Streamed answer (markdown) |
| `message-metadata` | `{messageMetadata: {route, model, usage}}` | Router decision and token usage |
| `finish` | `{finishReason?}` | End of message |
| `error` | `{errorText}` | Mid-stream failure; `errorText` is user-facing copy (localized) |

We do not stream tool inputs (`tool-input-start/delta` are not emitted). Tools are rendered by the
UI as parts of type `tool-<toolName>`.

`ProductCard`: `{id, name, categoryId, priceBrl, promoPriceBrl|null, discountPercent|null,
availability: "in_stock"|"out_of_stock"|"coming_soon"|"discontinued"}` — nullable fields are
always present.

`messageMetadata`: `{route: {intent, confidence, router: "jev"|"haiku"|"fake"}, model,
usage: {inputTokens, outputTokens}}`.

### Tool names and UI status labels (pt-BR)

| `toolName` | Label while running |
|---|---|
| `search_products` | Buscando no catálogo… |
| `get_product` | Consultando o produto… |
| `find_similar_products` | Procurando opções parecidas… |
| `get_active_promotions` | Verificando promoções… |
| `calculate_payment_options` | Calculando formas de pagamento… |
| `get_order_status` | Consultando seu pedido… |
| `search_policies` | Consultando as políticas da loja… |
| `get_store_info` | Buscando informações da loja… |
| `request_return` | Abrindo solicitação de devolução… |
| `register_complaint` | Registrando sua reclamação… |
| `handoff_to_human` | Chamando um atendente… |

Unknown tool names fall back to "Consultando…".

## Response (errors before streaming)

JSON body `{"error": {"code", "message", "retryAfterSeconds?"}}`; `message` is user-facing copy.

| Status | `code` | UI behaviour | Fixture |
|---|---|---|---|
| 400 | `invalid_request` | Generic error + retry | — |
| 401 | `unauthorized` | Redirect to login | `http-401.json` |
| 429 | `rate_limited` | Show message; disable input for `Retry-After` s | `http-429-rate-limited.json` |
| 429 | `budget_exhausted` | Show message; disable input until reset | `http-429-budget-exhausted.json` |
| 500 | `internal_error` | Show message + retry button | `http-500.json` |

## Fixtures and tests

| Fixture | Scenario |
|---|---|
| `plain-text.sse` | Greeting, text only, with metadata |
| `tool-products.sse` | Catalog search → tool call + `data-products` + answer |
| `tool-error.sse` | Order lookup fails verification → tool error + recovery text |
| `stream-error.sse` | Failure mid-answer → `error` chunk |
| `http-*.json` | Status, headers and body for each error above |
| `request-submit.json` | Request body example |

- **Frontend** (`frontend/src/lib/chat/contract.test.ts`): every `.sse` fixture parses with the
  AI SDK's own `uiMessageChunkSchema` and assembles into the expected `UIMessage` parts.
- **Backend** (`backend/tests/test_chat_contract.py`): the Pydantic models in
  `app/chat/protocol.py` parse every fixture and the encoder re-emits it **byte for byte**; error
  and request fixtures validate against their schemas. The agent (#6) must emit through this
  encoder, so a real-output contract test is added there.

Changing the contract means changing the fixtures first; both test suites then point at every
place that must follow.
