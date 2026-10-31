# Data Model: Chat web (003)

All types live in the frontend (`frontend/src/lib/chat/types.ts`) and mirror the #4 contract
(`docs/contracts/chat-stream.md`). Nothing is persisted; state lives in `useChat` for the page
session.

## ChatMessage

`UIMessage<ChatMetadata, ChatDataParts>` (AI SDK).

| Field | Type | Notes |
|---|---|---|
| `id` | string | From `start.messageId` (assistant) or generated (user) |
| `role` | `"user" \| "assistant"` | `system` never rendered |
| `parts` | `UIMessagePart[]` | Rendered in order; see Message part |
| `metadata` | `ChatMetadata?` | Not displayed |

## Message part (rendered subset)

| Part `type` | Source chunks | Rendered as |
|---|---|---|
| `text` | `text-start/delta/end` | Markdown (Streamdown) |
| `tool-<toolName>` | `tool-input-available`, `tool-output-available`, `tool-output-error` | `ToolStatus` |
| `data-products` | `data-products` | `ProductCards` |
| `step-start`, anything else | `start-step`, future chunks | Ignored |

### Tool part state → display state

| AI SDK `state` | `ToolDisplayState` |
|---|---|
| `input-streaming`, `input-available`, approval states | `running` |
| `output-available` | `done` |
| `output-error` | `failed` |

Label: `messages.tools[toolName] ?? messages.tools.fallback` ("Consultando…").

## ChatDataParts / ProductCard

```ts
type Availability = "in_stock" | "out_of_stock" | "coming_soon" | "discontinued";
type ProductCard = {
  id: number; name: string; categoryId: number;
  priceBrl: number; promoPriceBrl: number | null; discountPercent: number | null;
  availability: Availability;
};
type ChatDataParts = { products: { products: ProductCard[] } };
```

Display rules (formatting only — no computation, constitution I):
- `promoPriceBrl !== null` → show promo price large, `priceBrl` struck through, and
  `discountPercent` as "-N%" when not null.
- Otherwise → show `priceBrl`.
- Currency: `formatBrl(value, locale)` → `Intl.NumberFormat(locale, {style: "currency", currency: "BRL"})`.
- Discount: `formatPercent(20)` → "20%". The value is already a percentage, so it is formatted as
  an integer + `%`, **not** with Intl `style: "percent"` (which would print "2.000%").
- Availability badge label from `messages.availability[availability]`; unknown value → hidden.

## ChatMetadata

`{ route: { intent: string; confidence: number; router: "jev" | "haiku" | "fake" }; model: string;
usage: { inputTokens: number; outputTokens: number } }` — typed for completeness, never shown.

## ChatErrorState

Produced by `toChatError(error)` (pure), plus the local dropped-stream error set in `onFinish`.

| `kind` | From | Message | Action | Input |
|---|---|---|---|---|
| `unauthorized` | 401 `unauthorized` | — (redirect) | `router.replace("/login?reason=expired&callbackUrl=/")` | — |
| `rate_limited` | 429 `rate_limited` | body `message` | countdown; at 0 → "Tentar novamente" (`regenerate`) | disabled for body `retryAfterSeconds` s (default 60; headers unavailable) |
| `budget_exhausted` | 429 `budget_exhausted` | body `message` | none | disabled for page session; body `retryAfterSeconds` ignored |
| `retryable` | 400, 500, other status, network, mid-stream `error` chunk, unparseable body, stream ended with no finish reason and not aborted (`onFinish`) | body `message`; bare-`Error` `errorText`; otherwise catalog fallback (never SDK error text) | "Tentar novamente" | enabled |

A customer Stop (`onFinish` with `isAbort: true`) produces **no** error state.

```ts
type ChatErrorState =
  | { kind: "unauthorized" }
  | { kind: "rate_limited"; message: string; retryAfterSeconds: number }
  | { kind: "budget_exhausted"; message: string }
  | { kind: "retryable"; message: string };
```

## Chat UI state (derived)

| Condition | UI |
|---|---|
| `messages.length === 0` | Empty state (greeting + suggestions) |
| `status === "submitted"`, or `streaming` with no visible part yet in the last assistant message | Typing indicator |
| `status in {submitted, streaming}` | Stop button replaces Send; sending blocked |
| `status === "error"` | `ChatError` below the last message per `ChatErrorState` |
| blank input | Send disabled (input has `maxLength` 2000) |
| send already in flight (`sendingRef`) | Further sends ignored |

## Message catalog

`Messages` type = shape of `src/lib/i18n/pt-BR.ts`, read in components via `useMessages()`:
`app` (title, store name), `emptyState` (greeting, suggestions[]), `input` (placeholder, send,
stop, counter), `status` (typing), `tools` (11 contract tool names + `fallback`), `toolState`
(done/failed a11y suffixes), `availability` (4 values), `product` (discount, promo a11y),
`errors` (fallback, retry, rateLimitedCountdown with `{seconds}`, budget), `login`
(sessionExpired, placeholder), `markdown` (Streamdown `translations` subset in pt-BR).
