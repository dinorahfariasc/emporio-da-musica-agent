# Feature Specification: Chat web

**Feature Branch**: `dinorahfariasc/chat-web`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "003 Chat web: chat UI for Melody (Empório da Música customer-service
agent) consuming the chat stream contract from issue #4. Scope per issue #9: streaming answers,
tool-activity indicators, markdown rendering, product cards, error/retry/empty states,
Portuguese-first copy centralized for a later PT/EN switch, dev mock replaying the #4 fixtures,
default component styling (branding later via Figma, #18). Acceptance: every #4 fixture renders
correctly from the mock (plain, tool call, products, error, 429); distinct UI states for 401
(redirect to login), 429 (budget/rate message), 500 (retry); works at 375 px without horizontal
scroll; lint, typecheck and build pass in CI."

**Epic**: #9 · **Depends on**: #4 (merged — [`docs/contracts/chat-stream.md`](../../docs/contracts/chat-stream.md),
`contracts/chat-stream/fixtures/`), #3 (merged — frontend scaffolding, CI, mock route) ·
**Related**: #10 (auth, limits, deploy), #12 (history), #13 (PT/EN switch), #16 (Playwright),
#18 (Figma branding), #20 (product cards polish)

## Clarifications

### Session 2026-10-31

- Q: Should the chat be the whole page, or a widget floating on top of a simple store landing page? → A: Full-page chat at `/` (header with Melody/store name, conversation, input pinned to the bottom).
- Q: How should product results (the `data-products` part) be shown before #20? → A: Basic product cards now in this epic, built only from the contract's `ProductCard` fields (the contract has no image field, so cards have no image); #20 is left with branded/polished card variants. Confirmed over the contract doc's "markdown in P0" note.
- Q: Before #10 builds the real login, where should a 401 response send the customer? → A: Redirect to `/login?reason=expired`; this epic ships a minimal placeholder `/login` page (notice only, no form) that #10 replaces.
- Review (PR #32, QA + senior) → applied:
  - Markdown blocks all images and allow-lists link protocols (exfiltration blocker).
  - Production fails closed to the real backend.
  - A dropped stream is detected explicitly; a user Stop is not an error.
  - SDK error text is never shown.
  - Double-send is guarded.
  - Retry-after comes from the body only.
  - The 401 redirect carries `callbackUrl=/` (Auth.js).
  - Copy is read through a hook.
  - Scope is cut to 3 PRs.

## User Scenarios & Testing *(mandatory)*

The primary user is a store customer (in practice, a reviewer acting as one) who talks
to Melody, the store's virtual assistant, on a full-page chat. In development and CI the chat
runs against the existing mock, which replays the #4 contract fixtures (a fixture is selected by
sending `/fixture <name>` as the message), so the whole UI can be built and verified before the
real agent exists.

Contract fixtures referenced below: `plain-text`, `tool-products`, `tool-error`, `stream-error`,
`http-401`, `http-429-rate-limited`, `http-429-budget-exhausted`, `http-500`.

### User Story 1 - Ask Melody and see the answer stream in (Priority: P1)

A customer opens the chat, types a question in Portuguese (e.g. "Vocês têm violão até mil
reais?"), sends it, and sees Melody's answer appear progressively and formatted (paragraphs,
lists, bold, links), then asks the next question in the same conversation.

**Why this priority**: this is the product. Without a working send → streamed answer loop there is
nothing to evaluate.

**Independent Test**: with the mock replaying `plain-text`, send a message and verify the user
bubble appears immediately, the assistant answer grows incrementally, markdown is rendered, and
the input is usable again when the answer completes.

**Acceptance Scenarios**:

1. **Given** an empty conversation, **When** the page opens, **Then** an empty state shows a
   Portuguese greeting from Melody and 3–4 suggested questions.
2. **Given** the empty state, **When** the customer clicks a suggested question, **Then** it is
   sent exactly as if typed.
3. **Given** a typed message, **When** the customer presses Enter or the send button, **Then** the
   message appears as a user bubble at once, the input clears, and a "Melody está digitando…"
   indicator shows until the first assistant content (text or tool activity) arrives.
4. **Given** an answer is streaming, **When** text chunks arrive, **Then** they are appended to
   the same assistant bubble in order and rendered as markdown, and the view stays scrolled to
   the newest content unless the customer has scrolled up.
5. **Given** an answer is streaming, **When** the customer presses "Parar", **Then** streaming
   stops, the partial answer stays visible, and the customer can send a new message.
6. **Given** Shift+Enter in the input, **Then** a new line is inserted instead of sending; an
   empty or whitespace-only message cannot be sent.
7. **Given** an answer contains raw HTML (`<script>`, `<img onerror>`, `<iframe>`), a
   `javascript:` or `data:` link, or a markdown image `![](https://…)`, **Then** nothing executes,
   no image is rendered or requested, and no unsafe link is clickable.
8. **Given** an answer is streaming, **When** the customer presses "Parar", **Then** no error
   notice appears and the input is usable at once (a user stop is not a failure).
9. **Given** the customer presses Enter twice or double-clicks Send quickly, **Then** exactly one
   message is sent and one user bubble appears.

---

### User Story 2 - See what Melody is checking and the products it found (Priority: P1)

When Melody consults the store system, the customer sees a short Portuguese status line such as
"Buscando no catálogo…" that resolves when the check finishes; when products are returned, they
appear as product cards next to Melody's explanation.

**Why this priority**: tool calls are the main source of latency, and the store manual demands
answers grounded in the system; status lines and product cards make that grounding visible.

**Independent Test**: replay `tool-products` and `tool-error` and verify the status indicator
uses the contract's pt-BR label, reaches a done or failed state, and that the two products of
`tool-products` render as cards with the exact values from the stream.

**Acceptance Scenarios**:

1. **Given** the stream announces a tool call (part `tool-<toolName>`), **Then** an in-progress
   indicator shows the pt-BR label from the contract's tool-name table (e.g. `search_products` →
   "Buscando no catálogo…").
2. **Given** a tool indicator in progress, **When** the tool output arrives, **Then** the
   indicator shows a completed state and stops animating.
3. **Given** a tool fails (`output-error`, e.g. `get_order_status` with `verification_failed` in
   `tool-error`), **Then** the indicator shows a neutral failure state in Portuguese, the raw
   error code is not shown, and the recovery text that follows still renders.
4. **Given** a tool name not listed in the contract, **Then** the fallback label "Consultando…" is
   used instead of the technical name.
5. **Given** the stream carries a `data-products` part, **Then** each product is shown as a basic
   card with its name, price, availability badge and — when `promoPriceBrl`/`discountPercent`
   are not null — the promo price, the struck-through original price and the discount %.
   Prices are only formatted for display (pt-BR currency); no price, discount, stock or
   eligibility is computed by the UI.
6. **Given** several tool calls in one answer, **Then** each has its own indicator, in stream
   order.

---

### User Story 3 - Understand and recover from errors and limits (Priority: P1)

When something goes wrong, the customer sees a clear Portuguese message that matches the actual
situation and a way forward: log in again (session expired), wait (limit reached), or retry
(temporary failure).

**Why this priority**: the public deployment is protected by authentication and per-user limits
(#10); without distinct states the reviewer would hit an opaque failure and conclude the app is
broken.

**Independent Test**: replay `http-401`, `http-429-rate-limited`, `http-429-budget-exhausted`,
`http-500` and `stream-error`, and verify each produces its own distinct state and recovery
action as defined by the contract's error-code table.

**Acceptance Scenarios**:

1. **Given** the response is 401 `unauthorized`, **Then** the customer is redirected to
   `/login?reason=expired&callbackUrl=/`, where a placeholder page shows "Sua sessão expirou" (the login form
   itself is #10).
2. **Given** the response is 429 `rate_limited`, **Then** the server's message is shown inline,
   the input is disabled for the body's `retryAfterSeconds` (default 60 s; the SDK does not expose
   response headers) with a visible countdown, and re-enabled automatically afterwards together with a "Tentar
   novamente" button that resends the unanswered message (no second user bubble).
3. **Given** the response is 429 `budget_exhausted`, **Then** the server's message is shown inline
   and the input stays disabled for the rest of the page session (until reset); no retry button
   is offered.
4. **Given** the response is 500 `internal_error`, 400 `invalid_request`, or a network failure,
   **Then** an inline error shows the server message (or a catalog fallback when there is none)
   with a "Tentar novamente" button that resends the last user message without duplicating it.
5. **Given** an `error` chunk arrives mid-stream (`stream-error`), **Then** the partial text stays
   visible, the chunk's `errorText` (user-facing copy) is shown below it, and "Tentar novamente"
   is offered.
6. **Given** any error state, **Then** no status codes, error codes, stack traces or JSON are shown
   to the customer.

---

### User Story 4 - Use the chat comfortably on a phone (Priority: P2)

The reviewer may open the link on a phone. The chat must be fully usable at 375 px wide: no
horizontal scrolling, input always reachable, long content (URLs, tables, product names) wraps or
scrolls inside its own container.

**Why this priority**: required by the epic's acceptance criteria, but it builds on stories 1–3
rather than delivering standalone value.

**Independent Test**: at a 375 × 667 viewport, replay every fixture and verify the page never
scrolls horizontally and the input stays visible at the bottom.

**Acceptance Scenarios**:

1. **Given** a 375 px viewport, **When** any fixture is replayed, **Then** the document width
   never exceeds the viewport width.
2. **Given** an answer with a long unbroken URL or a markdown table, **Then** it wraps or scrolls
   within the bubble only.
3. **Given** product cards at 375 px, **Then** they stack in one column; on wider screens they may
   form a grid.
4. **Given** a phone viewport, **Then** the input area stays pinned to the bottom and tap targets
   are at least 44 px.

---

### Edge Cases

- Stream ends without a `finish` chunk and was not stopped by the customer (connection dropped):
  the SDK ends it as a normal completion, so the UI detects it (no finish reason, not aborted, not
  errored) and shows a retryable error; partial text kept. A customer Stop never shows an error.
- Unknown chunk/part types (future contract additions, e.g. other `data-*` parts): ignored
  without breaking the render.
- `message-metadata` (route, model, usage) is not shown to the customer.
- Very long answers: the conversation scrolls; incremental markdown rendering does not freeze the
  page, and incomplete markdown mid-stream (unclosed `**`, half table) does not flash broken
  layout.
- Customer tries to send while an answer is streaming: sending is blocked until the answer ends
  or is stopped.
- `data-products` with an empty list: nothing is rendered for it (the text answer explains).
- Product with very long name: the name wraps (or clamps to 2 lines with full name available
  to assistive technology) inside the card.
- Message longer than 2,000 characters: the input does not accept more characters.
- Rapid repeated send (double Enter/click): only the first is sent.
- Page reload: conversation is lost (persistence is #12); the empty state shows again.
- Customer writes in English: the UI chrome stays Portuguese (the agent answers in the customer's
  language; UI switching is #13).
- Error response with a body that does not match the contract (e.g. HTML from a proxy): treated as
  a generic error with the catalog fallback message and retry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The chat MUST send the customer's message with the conversation to the existing
  `/api/chat` endpoint using the request shape of the #4 contract, keeping one stable chat `id`
  per page session, and render the response as it streams.
- **FR-002**: The chat MUST render assistant text as sanitized markdown (paragraphs, lists,
  emphasis, links, inline code, tables), opening links in a new tab and tolerating incomplete
  markdown while streaming. It MUST NOT execute or render raw HTML, MUST NOT render or request
  any image (markdown or HTML, including `data:`), MUST only make `https:`, `http:` and `mailto:`
  links clickable, and MUST NOT show the renderer's copy/download controls.
- **FR-003**: The chat MUST show a typing indicator between sending and the first assistant
  content, and a stop control while an answer streams.
- **FR-004**: The chat MUST render one activity indicator per `tool-<toolName>` part using the
  contract's pt-BR label table, with in-progress, done and failed states, the fallback label
  "Consultando…" for unknown tools, and never show tool inputs, outputs or error codes.
- **FR-005**: The chat MUST render each `data-products` part as basic product cards showing only
  the contract's `ProductCard` values: name, price, availability badge (pt-BR label for
  `in_stock`, `out_of_stock`, `coming_soon`, `discontinued`), and promo price + struck-through
  original price + discount % when those fields are not null. The UI only formats values for
  display (pt-BR currency, percentage); it MUST NOT compute price, discount, stock or
  eligibility (constitution principle I).
- **FR-006**: The chat MUST show an empty state with a greeting from Melody and 3–4 suggested
  questions that send on click.
- **FR-007**: The chat MUST map error responses to the contract's error-code table: 401
  `unauthorized` → redirect to `/login?reason=expired&callbackUrl=/`; 429 `rate_limited` → message + input
  disabled with a countdown for the body's `retryAfterSeconds` (default 60 s); 429 `budget_exhausted` →
  message + input disabled for the page session (its `retryAfterSeconds` is ignored), no retry;
  when the `rate_limited` countdown ends, retry is offered as well; 500 `internal_error`, 400
  `invalid_request`, network failure, mid-stream `error` chunks and streams that end without a
  finish reason (not aborted by the customer) → message + retry.
- **FR-008**: Error copy MUST come from the server (`error.message` of a contract error body, or
  the `error` chunk's `errorText`, which the contract defines as user-facing), falling back to the
  message catalog when absent or unparseable. Text of SDK/internal errors (validation, JSON parse,
  network) MUST never be shown.
- **FR-009**: Retry MUST resend the last user message without duplicating it in the visible
  conversation.
- **FR-010**: All UI copy (labels, notices, suggestions, tool status labels, availability labels,
  accessibility labels, fallbacks, and the markdown renderer's built-in strings) MUST live in a
  single centralized pt-BR message catalog keyed by identifier and be read by components through
  one hook, with locale-aware formatting and the document `lang` set from the active locale, so an
  English catalog (#13) can be added without touching components.
- **FR-011**: Development and CI MUST work entirely against the existing mock mode (`CHAT_MODE=mock`,
  `/fixture <name>`) with no backend and no API key. In production, an unset `CHAT_MODE` MUST
  resolve to the real backend (fail closed); the mock runs in production only when explicitly
  configured.
- **FR-012**: The site MUST include a placeholder `/login` page that shows the session-expired
  notice when `reason=expired` is present; it contains no login form (#10 replaces it).
- **FR-013**: The layout MUST work from 375 px width upward with no horizontal page scroll, a
  bottom-pinned input, and tap targets ≥ 44 px.
- **FR-014**: The chat MUST be keyboard-operable (Enter sends, Shift+Enter inserts a newline,
  focus returns to the input after sending and after retry), announce new assistant content to
  screen readers through a polite live region, and expose error notices with an alert role.
- **FR-015**: Visual styling MUST use design tokens in `globals.css` (not one-off hex in every
  component). The default shadcn theme was the 003 baseline; Figma branding (#18,
  `specs/008-figma-branding`) replaces those tokens and restyles surfaces. Behaviour in FR-001–
  FR-014 is unchanged.
- **FR-016**: Lint, typecheck, tests and production build MUST pass in CI; automated tests MUST
  cover rendering of every `.sse` fixture and every `http-*` error state.
- **FR-017**: The chat MUST NOT log message content or personal data to the browser console or
  third-party services (constitution principle V).
- **FR-018**: The chat MUST be the full page at the site root (`/`): a header with the store name
  and Melody's identity, the conversation area, and the input pinned to the bottom. No landing
  page or floating widget in this epic.
- **FR-019**: A send MUST be ignored while a previous send is being submitted, so rapid repeated
  input produces exactly one request.

### Key Entities

- **Conversation**: the ordered list of messages in the current page session, with a stable chat
  id; not persisted.
- **Message**: author (customer or Melody), ordered parts, optional metadata (not displayed).
- **Message part**: `text` (markdown), `tool-<toolName>` (state: in progress / done / failed),
  `data-products` (list of product cards), or ignored unknown parts.
- **Product card**: display-only view of one contract `ProductCard` — id, name, categoryId,
  priceBrl, promoPriceBrl (nullable), discountPercent (nullable), availability.
- **Chat error state**: kind (unauthorized, rate-limited, budget-exhausted, retryable failure),
  user-facing message, optional retry-after seconds, and the recovery action it allows.
- **Message catalog**: pt-BR strings keyed by identifier, including the tool-name → status-label
  and availability → label mappings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the `.sse` fixtures (`plain-text`, `tool-products`, `tool-error`,
  `stream-error`) render as specified, verified by automated tests.
- **SC-002**: Each of the four `http-*` fixtures (401, 429 rate, 429 budget, 500) produces a
  visibly distinct state with its own recovery action, verified by automated tests.
- **SC-003**: The user bubble and typing indicator appear immediately on send, before the answer
  (checked by order in the flow test and manually); streamed text appears incrementally.
- **SC-004**: At 375 px width, 0 fixtures cause horizontal page scroll (manual check with a
  screenshot in the final PR; automated in #16).
- **SC-005**: 0 hard-coded customer-facing strings in chat components outside the message catalog.
- **SC-006**: Lint, typecheck, tests and production build pass in CI with no backend and no API
  keys.
- **SC-007**: A first-time user gets an answer in one click by choosing a suggested question.
- **SC-008**: Product card values match the stream exactly for 100% of products in the
  `tool-products` fixture (name, prices, discount, availability label).

## Assumptions

- The #4 contract (`docs/contracts/chat-stream.md`) is the source of truth; if it changes, its
  fixtures change first and this feature's tests follow.
- The existing `/api/chat` route and mock (`frontend/src/lib/chat/mock.ts`) from #3/#4 are reused;
  this epic only changes the production default (FR-011). Auth on the route and the session gate
  (in `proxy.ts`, keeping `/` prerendered) belong to #10.
- Login form, session handling and real limits belong to #10; this epic only reacts to 401/429.
- One conversation per page session; no history, no multiple conversations (#12).
- Basic product cards shipped in this epic; branded/polished card variants are #18 / #20
  (`specs/008-figma-branding`). Cards have no image because the contract's `ProductCard` has no
  image field.
- PT/EN switch (#13), Playwright smoke tests (#16) and human-in-the-loop confirmation UI (#14)
  remain out of scope. Figma branding is specified in `specs/008-figma-branding` (epic #18).
- Maximum input length is 2,000 characters (`maxLength` on the input; the backend enforces its
  own limits).
