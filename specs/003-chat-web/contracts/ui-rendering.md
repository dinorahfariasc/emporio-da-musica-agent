# UI rendering contract: fixture → expected UI (003)

This feature exposes no new API. It *consumes* the #4 contract
([`docs/contracts/chat-stream.md`](../../../docs/contracts/chat-stream.md)); this table fixes what
the UI must show for each fixture and is the basis of the component tests. If a fixture changes,
this table and its test change with it.

| Fixture | Expected UI | Spec |
|---|---|---|
| `plain-text.sse` | One assistant bubble with the markdown-rendered text; no tool status; no products; metadata not shown | US1, FR-002 |
| `tool-products.sse` | `ToolStatus` "Buscando no catálogo…" in done state; 2 product cards: "Tagima Woodstock Dreadnought Natural" R$ 899,00 and "Yamaha F310 Aço Natural" R$ 699,90, both "Em estoque"; then the answer text | US2, FR-004/005 |
| `tool-error.sse` | `ToolStatus` "Consultando seu pedido…" in failed state, code `verification_failed` not visible; recovery text rendered | US2 #3 |
| `stream-error.sse` | Partial text "Deixa eu verificar isso pra você" kept; error notice with the chunk's `errorText`; "Tentar novamente" button | US3 #5 |
| `http-401.json` | `router.replace("/login?reason=expired")` called; no inline error | US3 #1 |
| `http-429-rate-limited.json` | Notice with the body `message`; input + send disabled; countdown from 30 s; at 0 input re-enabled and "Tentar novamente" shown (resends, no duplicate bubble) | US3 #2 |
| `http-429-budget-exhausted.json` | Notice with the body `message`; input + send disabled; no retry button; stays disabled | US3 #3 |
| truncated `plain-text` (no `finish`, test-only) | Partial text kept; retryable notice with catalog fallback + "Tentar novamente" | Edge Cases |
| `http-500.json` | Notice with the body `message`; "Tentar novamente" resends without a duplicate user bubble | US3 #4, FR-009 |

## Component interfaces (internal)

| Component | Props | Notes |
|---|---|---|
| `Chat` | `{ fetch?: typeof fetch }` | Owns `useChat`; `fetch` is injectable for tests only |
| `MessageView` | `{ message: ChatMessage }` | Pure: renders parts in order |
| `ToolStatus` | `{ toolName: string; state: ToolDisplayState }` | Label from catalog |
| `ProductCards` | `{ products: ProductCard[] }` | Renders nothing for `[]` |
| `Markdown` | `{ children: string; streaming?: boolean }` | Streamdown wrapper |
| `ChatInput` | `{ disabled; busy; onSend(text); onStop() }` | Enter / Shift+Enter, 2,000-char guard |
| `ChatError` | `{ error: ChatErrorState; onRetry() }` | Countdown for `rate_limited` |
| `EmptyState` | `{ onPick(text) }` | Greeting + suggestions |

`toChatError(error: Error): ChatErrorState` — pure, see [data-model.md](../data-model.md).
