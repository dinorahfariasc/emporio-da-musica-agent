---

description: "Task list for 003 Chat web (epic #9)"
---

# Tasks: Chat web

**Input**: Design documents from `specs/003-chat-web/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/ui-rendering.md](contracts/ui-rendering.md)

**Tests**: Required — FR-016 asks for automated coverage of every `.sse` fixture and every `http-*`
error state, and constitution IV requires tests before done. Within each story, write the test
first and see it fail.

**Organization**: grouped by user story. Paths are relative to the repository root; frontend
commands run in `frontend/`. Before using any `ai`, `@ai-sdk/react`, `streamdown` or Next API,
check its type definitions in `frontend/node_modules` and `frontend/node_modules/next/dist/docs/`
(see `frontend/AGENTS.md`). Never add `export const dynamic`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: user story from spec.md (US1–US4)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: test tooling and UI primitives. PR slice 1 (with Phase 2), body "Part of #9".

- [ ] T001 Add dev deps `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom` and runtime dep `streamdown` with `pnpm add` in `frontend/package.json` (lockfile updated)
- [ ] T002 Create `frontend/vitest.config.ts`: `@/` → `src/` alias, two `test.projects` (node for `**/*.test.ts`, jsdom for `**/*.test.tsx`; `environmentMatchGlobs` is gone in recent vitest — confirm in `node_modules/vitest` types), `setupFiles: ["src/test/setup.ts"]`; keep `src/lib/chat/contract.test.ts` passing
- [ ] T003 [P] Create `frontend/src/test/setup.ts` importing `@testing-library/jest-dom/vitest` and calling `cleanup()` after each test; add `TextDecoderStream`/`ReadableStream` polyfill only if a jsdom test proves it is missing
- [ ] T004 [P] Add shadcn primitives with `pnpm dlx shadcn@latest add textarea card badge alert` into `frontend/src/components/ui/` (base-nova style, no edits to generated files beyond lint fixes)
- [ ] T005 Verify `pnpm lint && pnpm typecheck && pnpm test && pnpm build` pass in `frontend/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: types, catalog, pure mappers and fixture helpers used by every story.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

- [ ] T006 Create `frontend/src/test/fixtures.ts` by extracting from `src/lib/chat/contract.test.ts`: `FIXTURES_DIR`, `readFixture(name)`, `parseChunks(name)`, `assembleMessage(name): Promise<ChatMessage>` (via `readUIMessageStream`), and `fixtureFetch(name)` returning a `typeof fetch` that serves `.sse` files as a `text/event-stream` Response with `x-vercel-ai-ui-message-stream: v1`, and `http-*.json` files as `Response.json(body, {status, headers})`; optional `sequence` form (array of names served in order) for retry tests, a `{truncate: true}` option that drops the `finish` chunk and `[DONE]` from an `.sse` fixture, and a `pending` option that holds the response until released (for SC-003)
- [ ] T007 Refactor `frontend/src/lib/chat/contract.test.ts` to import the helpers from `src/test/fixtures.ts` (behaviour unchanged, still green)
- [ ] T008 [P] Create `frontend/src/lib/chat/types.ts`: `Availability = "in_stock" | "out_of_stock" | "coming_soon" | "discontinued"`; `ProductCard = {id: number; name: string; categoryId: number; priceBrl: number; promoPriceBrl: number | null; discountPercent: number | null; availability: Availability}` ("nullable fields are always present"); `ChatDataParts = {products: {products: ProductCard[]}}`; `ChatMetadata = {route: {intent: string; confidence: number; router: "jev" | "haiku" | "fake"}; model: string; usage: {inputTokens: number; outputTokens: number}}`; `ChatMessage = UIMessage<ChatMetadata, ChatDataParts>`
- [ ] T009 [P] Create `frontend/src/lib/i18n/pt-BR.ts` (catalog, `as const`, exported type `Messages`) with sections `app`, `emptyState` (greeting + 4 suggestions, e.g. "Vocês têm violão até R$ 1.000?", "Quais promoções estão ativas?", "Como faço para trocar um produto?", "Quais as formas de pagamento?"), `input` (placeholder, send, stop, counter `{count}/{max}`), `status` ("Melody está digitando…"), `tools` (the 11 contract labels verbatim: `search_products` "Buscando no catálogo…", `get_product` "Consultando o produto…", `find_similar_products` "Procurando opções parecidas…", `get_active_promotions` "Verificando promoções…", `calculate_payment_options` "Calculando formas de pagamento…", `get_order_status` "Consultando seu pedido…", `search_policies` "Consultando as políticas da loja…", `get_store_info` "Buscando informações da loja…", `request_return` "Abrindo solicitação de devolução…", `register_complaint` "Registrando sua reclamação…", `handoff_to_human` "Chamando um atendente…", `fallback` "Consultando…"), `toolState` (done/failed suffixes), `availability` (in_stock "Em estoque", out_of_stock "Esgotado", coming_soon "Em breve", discontinued "Fora de linha"), `product` (discount "-{percent}%", original price a11y), `errors` (fallback, retry "Tentar novamente", countdown "Você poderá enviar em {seconds}s"), `login` (sessionExpired "Sua sessão expirou. Entre novamente para continuar.", placeholder note "O login estará disponível em breve." — no issue numbers in user-facing copy)
- [ ] T010 [P] Create `frontend/src/lib/i18n/index.ts` exporting `messages` (pt-BR for now) and `format(template, vars)` for `{name}` interpolation; unit test `frontend/src/lib/i18n/index.test.ts` (interpolation; every contract tool name has a `tools` label — parse the table rows under the `### Tool names and UI status labels` heading of `docs/contracts/chat-stream.md` (rows like `` | `search_products` | … | ``) and assert exactly 11 names were found)
- [ ] T011 [P] Create `frontend/src/lib/format.ts` with `formatBrl(value: number)` (`Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"})`) and `formatPercent(value: number)`; test `frontend/src/lib/format.test.ts` (899 → "R$ 899,00", 699.9 → "R$ 699,90"; normalize NBSP in assertions)
- [ ] T012 [P] Create `frontend/src/lib/chat/tool-state.ts`: `toToolDisplayState(state)` mapping `input-streaming`/`input-available`/approval states → `running`, `output-available` → `done`, `output-error` → `failed`; `toolLabel(toolName)` → `messages.tools[toolName] ?? messages.tools.fallback`; test `frontend/src/lib/chat/tool-state.test.ts`
- [ ] T013 Write failing tests `frontend/src/lib/chat/errors.test.ts` for `toChatError`: build an `APICallError` from each `http-*.json` fixture (statusCode + `JSON.stringify(body)` as responseBody) → `unauthorized`; `rate_limited` with message from body and `retryAfterSeconds: 30`; `budget_exhausted` with body message; `retryable` with body message for 500; 400 `invalid_request` → `retryable`; non-JSON body (e.g. `<html>`) → `retryable` with `messages.errors.fallback`; `rate_limited` without `retryAfterSeconds` → 60; `new Error("<errorText>")` → `retryable` with that text; `TypeError("Failed to fetch")` and `AbortError` → `retryable` with fallback
- [ ] T014 Implement `frontend/src/lib/chat/errors.ts` (`ChatErrorState` union exactly as in data-model.md; uses `APICallError.isInstance` from `ai`) until T013 passes

**Checkpoint**: foundation ready — lint/typecheck/test/build green; open PR slice 1.

---

## Phase 3: User Story 1 — Ask Melody and see the answer stream in (Priority: P1) 🎯 MVP

**Goal**: full-page chat at `/` that sends messages and renders the streamed markdown answer.

**Independent Test**: render `<Chat fetch={fixtureFetch("plain-text")}/>`, send "Oi", see the user
bubble, typing indicator, then the assembled markdown answer; input usable again. PR slice 2.

### Tests for User Story 1 ⚠️ write first, see them fail

- [ ] T015 [P] [US1] `frontend/src/components/chat/message-view.test.tsx`: `assembleMessage("plain-text")` renders the text as markdown (e.g. bold → `<strong>`), metadata not rendered; a message with text `<script>alert(1)</script>` and `[x](javascript:alert(1))` renders no `<script>` and no anchor with a `javascript:` href
- [ ] T016 [P] [US1] `frontend/src/components/chat/chat-input.test.tsx`: Enter calls `onSend` with trimmed text and clears; Shift+Enter inserts newline; blank text cannot be sent; > 2,000 chars disables send and shows counter; when `busy` the Stop button calls `onStop` and send is blocked; when `disabled` textarea and buttons are disabled
- [ ] T017 [P] [US1] `frontend/src/components/chat/chat.test.tsx` (flow): empty state shows greeting + 4 suggestions; clicking a suggestion sends it; after send the user bubble and "Melody está digitando…" are on screen while the stub response is still `pending` (SC-003), then the `plain-text` answer renders and the polite live region contains its text once; second message in the same conversation reuses the same chat id (inspect stub fetch request bodies)

### Implementation for User Story 1

- [ ] T018 [P] [US1] `frontend/src/components/chat/markdown.tsx`: client wrapper around `Streamdown` (confirm props in `node_modules/streamdown` types) with incomplete-markdown parsing on while streaming, links `target="_blank" rel="noopener noreferrer"`, only `http(s)`/`mailto` links allowed, raw HTML not executed, tables/code wrapped in `overflow-x-auto`, `min-w-0 break-words`
- [ ] T019 [P] [US1] `frontend/src/components/chat/typing-indicator.tsx` (catalog `status.typing`, `role="status"`, animated dots via Tailwind `animate-pulse`, respects `motion-reduce`)
- [ ] T020 [P] [US1] `frontend/src/components/chat/empty-state.tsx` (`{onPick(text)}`; greeting + suggestion buttons from `messages.emptyState`, ≥ 44 px targets)
- [ ] T021 [P] [US1] `frontend/src/components/chat/chat-input.tsx` (`{disabled, busy, onSend, onStop}`; shadcn `Textarea` + `Button`; 2,000-char max; counter shown above 1,800; focus returned to textarea after send) until T016 passes
- [ ] T022 [US1] `frontend/src/components/chat/message-view.tsx` (`{message: ChatMessage, streaming?: boolean}`): user bubble right / assistant left; iterate `parts` in order; `text` → `Markdown`; other part types → `null` for now (US2 extends); until T015 passes
- [ ] T023 [US1] `frontend/src/components/chat/message-list.tsx`: `role="log"` scroll container, renders `MessageView` per message, typing indicator slot, stick-to-bottom (auto-scroll only when within ~80 px of bottom), visually hidden `aria-live="polite"` region announcing each assistant message's text once it finishes
- [ ] T024 [P] [US1] `frontend/src/components/chat/chat-header.tsx` (store name + "Melody" from `messages.app`)
- [ ] T025 [US1] `frontend/src/components/chat/chat.tsx` (`"use client"`, `{fetch?: typeof fetch}`): `useChat<ChatMessage>({transport: new DefaultChatTransport({api: "/api/chat", fetch})})` (memoize transport); typing indicator when `status === "submitted"` or streaming with no visible part yet; `stop()` wired; `h-dvh` flex column header / list / pinned input; no `console.*` of message content (FR-017); until T017 passes
- [ ] T026 [US1] Replace `frontend/src/app/page.tsx` with the server page rendering `<Chat/>` (no `export const dynamic`); confirm `pnpm build` passes with Cache Components

**Checkpoint**: US1 works in `pnpm dev` with `CHAT_MODE=mock`; open PR slice 2.

---

## Phase 4: User Story 2 — See what Melody is checking and the products it found (Priority: P1)

**Goal**: tool status lines and basic product cards.

**Independent Test**: `tool-products` → done status "Buscando no catálogo…" + 2 cards with exact
values; `tool-error` → failed status, no code. PR slice 3.

### Tests for User Story 2 ⚠️ write first

- [ ] T027 [P] [US2] `frontend/src/components/chat/tool-status.test.tsx`: running/done/failed states render label + distinct state (accessible name includes state suffix); unknown tool → "Consultando…"; technical tool name never in the document
- [ ] T028 [P] [US2] `frontend/src/components/chat/product-cards.test.tsx`: products from `tool-products` render names "Tagima Woodstock Dreadnought Natural" / "Yamaha F310 Aço Natural", prices "R$ 899,00" / "R$ 699,90", badge "Em estoque"; a product with `promoPriceBrl: 160, priceBrl: 200, discountPercent: 20` shows "R$ 160,00", struck-through "R$ 200,00" (`<s>`/`line-through`) and "-20%"; an unknown `availability` value renders no badge; `[]` renders nothing; very long name wraps (`break-words`/`line-clamp-2` with full name in `title`/aria)
- [ ] T029 [P] [US2] Extend `frontend/src/components/chat/message-view.test.tsx`: `assembleMessage("tool-products")` renders tool status (done), 2 cards, then text, in that order; `assembleMessage("tool-error")` renders failed status, no "verification_failed" text, and the recovery text; unknown `data-*` part ignored without error

### Implementation for User Story 2

- [ ] T030 [P] [US2] `frontend/src/components/chat/tool-status.tsx` (`{toolName, state}` using `toolLabel`/`toToolDisplayState`; lucide `Loader2` spinning for running (`motion-reduce:animate-none`), `Check` for done, `AlertCircle` muted for failed; never renders input/output/errorText) until T027 passes
- [ ] T031 [P] [US2] `frontend/src/components/chat/product-cards.tsx` (`{products: ProductCard[]}`; shadcn `Card` + `Badge`; `grid grid-cols-1 sm:grid-cols-2 gap-2`; display-only formatting with `formatBrl`/`formatPercent`, no arithmetic on values — constitution I) until T028 passes
- [ ] T032 [US2] Extend `frontend/src/components/chat/message-view.tsx`: `isToolUIPart(part)` → `ToolStatus` with `getToolName(part)`; `part.type === "data-products"` → `ProductCards`; everything else ignored; until T029 passes

**Checkpoint**: US1 + US2 pass independently; open PR slice 3.

---

## Phase 5: User Story 3 — Understand and recover from errors and limits (Priority: P1)

**Goal**: distinct states for 401, 429 rate, 429 budget, 500/400/network and mid-stream errors.

**Independent Test**: flow tests with `fixtureFetch` for each `http-*` fixture and `stream-error`.
PR slice 4.

### Tests for User Story 3 ⚠️ write first

- [ ] T033 [P] [US3] `frontend/src/components/chat/chat-error.test.tsx`: `rate_limited` shows message + countdown decreasing with fake timers and calls `onExpire` at 0; `budget_exhausted` shows message and no retry button; `retryable` shows message + "Tentar novamente" calling `onRetry`; no status/error codes rendered
- [ ] T034 [US3] Extend `frontend/src/components/chat/chat.test.tsx` (mock `next/navigation` `useRouter`): `http-401` → `replace("/login?reason=expired")`; `http-429-rate-limited` → notice with fixture message, textarea disabled, re-enabled after 30 s (fake timers) with "Tentar novamente" shown; retry with `fixtureFetch(["http-429-rate-limited", "plain-text"])` answers with exactly one user bubble; `http-429-budget-exhausted` → disabled, no retry; `http-500` then retry with `fixtureFetch(["http-500", "plain-text"])` → answer rendered and exactly one user bubble; `stream-error` → partial "Deixa eu verificar isso pra você" kept + `errorText` shown + retry offered; truncated `plain-text` (`{truncate: true}`) → partial text kept + retryable notice with catalog fallback
- [ ] T035 [P] [US3] `frontend/src/components/login/login-notice.test.tsx`: with `?reason=expired` shows `messages.login.sessionExpired`; without it shows only the placeholder note

### Implementation for User Story 3

- [ ] T036 [P] [US3] `frontend/src/components/chat/chat-error.tsx` (`{error: ChatErrorState, onRetry, onExpire}`; shadcn `Alert`; countdown with `setInterval` cleared on unmount; copy from server message, fallback from catalog) until T033 passes
- [ ] T037 [US3] Wire errors in `frontend/src/components/chat/chat.tsx`: `const chatError = error && toChatError(error)`; effect on `unauthorized` → `router.replace("/login?reason=expired")`; `rate_limited` → input disabled until `onExpire`, then input re-enabled and retry offered (`clearError(); regenerate()`); `budget_exhausted` → input disabled for the page session (local `locked` state survives `clearError`); `retryable` → `onRetry = () => { clearError(); regenerate(); }`; a stream that closes without `finish` must end as `retryable` (check in `node_modules/ai` whether ai@7 raises an error for it; if not, detect it via `onFinish`/status and set a local error); render `ChatError` after the last message; until T034 passes
- [ ] T038 [P] [US3] `frontend/src/components/login/login-notice.tsx` (`"use client"`, `useSearchParams()`, `reason === "expired"` → shadcn `Alert` with catalog copy) until T035 passes
- [ ] T039 [US3] `frontend/src/app/login/page.tsx`: server page with a heading from `messages.login`, placeholder note from `messages.login` (user-facing, no issue numbers), and `<Suspense><LoginNotice/></Suspense>` (required under Cache Components); link back to `/`; `pnpm build` passes

**Checkpoint**: all P1 stories pass; open PR slice 4.

---

## Phase 6: User Story 4 — Use the chat comfortably on a phone (Priority: P2)

**Goal**: 375 px without horizontal scroll, pinned input, 44 px targets.

**Independent Test**: manual 375 × 667 replay of every fixture (quickstart.md) + layout-class test.

- [ ] T040 [P] [US4] `frontend/src/components/chat/layout.test.tsx`: render `Chat` after `tool-products` and a long-URL/table markdown message; assert root uses `h-dvh` flex column, message container and bubbles carry `min-w-0`, markdown table/code wrappers have `overflow-x-auto`, every button in the chat has `min-h-11`/`size-11` (≥ 44 px), no element has a fixed `w-[...px]` wider than 375
- [ ] T041 [US4] Apply responsive fixes in `frontend/src/components/chat/chat.tsx`, `message-list.tsx`, `message-view.tsx`, `markdown.tsx`, `product-cards.tsx`, `chat-input.tsx` until T040 passes (bubble `max-w-[85%] sm:max-w-[75%]`, `overflow-x-hidden` on the list, safe-area padding `pb-[env(safe-area-inset-bottom)]` on the input bar)
- [ ] T042 [US4] Set the viewport in `frontend/src/app/layout.tsx` via `export const viewport` (`width: "device-width", initialScale: 1, viewportFit: "cover"`; check `node_modules/next/dist/docs` for the Next 16 `viewport` export)

**Checkpoint**: all stories complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T043 [P] Copy audit: grep `frontend/src/components` and `frontend/src/app` for string literals in JSX shown to users; move any to `frontend/src/lib/i18n/pt-BR.ts` (SC-005); grep `frontend/src/components` for hard-coded colours (`#[0-9a-fA-F]{3,6}`, `rgb(`) — only theme tokens allowed (FR-015)
- [ ] T044 [P] Privacy audit: no `console.*` with message/part content in `frontend/src` (FR-017)
- [ ] T045 [P] Keyboard/a11y pass in `frontend/src/components/chat/`: focus returns to the input after send and after retry; buttons have accessible names from the catalog; live region announces finished answers once
- [ ] T046 Run [quickstart.md](quickstart.md) manually in `pnpm dev` (all rows + 375 px check) and record results in the final PR description
- [ ] T047 Update the DL-008 entry in `docs/decision-log.md` (added with the spec PR) with implementation outcomes: Streamdown choice, error mapping via `APICallError`, product cards pulled into #9, `/login` placeholder, role of AI
- [ ] T048 `pnpm lint && pnpm typecheck && pnpm test && pnpm build` green in `frontend/`; open final PR with `Closes #9`

---

## Dependencies & Execution Order

### Phase dependencies

- Setup (Phase 1) → Foundational (Phase 2) → US1 (Phase 3) → US2 / US3 → US4 → Polish.
- US2 and US3 each depend only on US1's `message-view.tsx` / `chat.tsx`; they touch different
  files except `message-view.tsx` (US2) and `chat.tsx` (US3), so they can run in parallel.
- US4 depends on all components existing.

### Within each story

- Tests first (must fail) → leaf components [P] → composite components → page wiring.

### Parallel opportunities

- Phase 1: T003, T004 in parallel after T001–T002.
- Phase 2: T008–T012 in parallel; T013 → T014 sequential.
- US1: T015–T017 together; then T018–T021, T024 together; then T022 → T023 → T025 → T026.
- US2: T027–T029 together; T030, T031 together; then T032.
- US3: T033, T035 together; T036, T038 together; then T037, T039.

### Parallel example: User Story 2

```text
Task: "T027 tool-status.test.tsx"     Task: "T028 product-cards.test.tsx"
Task: "T030 tool-status.tsx"          Task: "T031 product-cards.tsx"
```

## Implementation Strategy

### MVP first

1. Phase 1 + 2 (PR slice 1).
2. US1 (PR slice 2) → a streaming chat usable on the mock: **MVP**.
3. Stop and validate with the quickstart's first two rows.

### Incremental delivery

US2 (slice 3) → US3 (slice 4) → US4 + polish (slice 5, `Closes #9`). Each slice keeps lint,
typecheck, test and build green and is demoable on the mock. No implementation starts before the
spec PR passes QA + senior review.
