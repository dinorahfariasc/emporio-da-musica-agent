# Research: Chat web (003)

Versions verified against `frontend/node_modules` (not training data): `ai@7.0.x`,
`@ai-sdk/react@4.0.x`, `next@16.4.3` (Cache Components on), `react@19.3`, `vitest@5`,
shadcn `base-nova` style on `@base-ui/react`.

## R1 — Chat state: `useChat` with `DefaultChatTransport`

- **Decision**: `useChat<ChatMessage>()` from `@ai-sdk/react` with the default transport pointed at
  the existing `POST /api/chat`. `ChatMessage = UIMessage<ChatMetadata, ChatDataParts>` where
  `ChatDataParts = { products: { products: ProductCard[] } }`, so `data-products` parts are typed.
  Tools stay untyped (`UITools` default): tool parts are matched with `isToolUIPart()` +
  `getToolName()`, which are both exported by `ai@7`.
- **Rationale**: `useChat` already assembles the v1 UI message stream into `UIMessage` parts
  (exactly what `contract.test.ts` checks with `readUIMessageStream`), exposes `status`
  (`submitted | streaming | ready | error`), `stop()`, `regenerate()`, `clearError()` and
  `error`. The request body it sends matches the contract's `request-submit.json`.
- **Alternatives**: hand-rolled SSE reader (duplicates SDK logic); typing every tool in `UITools`
  (adds no value for display-only status and couples the UI to tool I/O schemas).

## R2 — HTTP error mapping (401/429/500)

- **Finding**: on a non-2xx response the HTTP transport throws
  `createUIApiCallError()` → `APICallError` with `statusCode` and `responseBody` (raw text);
  response headers are not retained. A mid-stream `error` chunk surfaces as `Error(errorText)`.
- **Decision**: one pure function `toChatError(error: Error): ChatErrorState` in
  `src/lib/chat/errors.ts`. It uses `APICallError.isInstance()`, parses `responseBody` as the
  contract body `{error: {code, message, retryAfterSeconds?}}` (safe-parse; non-JSON → generic),
  and maps `code` → kind. `retryAfterSeconds` comes from the body (the contract always sends it
  for `rate_limited`); a missing value falls back to 60 s. Non-`APICallError` errors are
  mid-stream/network → `retryable` with the error's message only if it came from an `error`
  chunk, otherwise the catalog fallback.
- **Telling network errors apart from `error` chunks**: `TypeError` (fetch failure) and
  `AbortError` are mapped to the catalog fallback; other plain `Error`s carry the contract's
  user-facing `errorText`.
- **Rationale**: a pure mapper is trivially unit-testable from the `http-*.json` fixtures.
- **Alternatives**: a custom `fetch` wrapper that inspects responses before the SDK (more code,
  same information); reading `Retry-After` header (not available through the SDK error).

## R3 — Retry semantics

- **Decision**: "Tentar novamente" calls `clearError()` then `regenerate()`. When the last message
  is an assistant message (partial answer from `stream-error`), `regenerate` replaces it; when
  the last message is the user's (HTTP error before streaming) it resubmits that message. The
  user bubble is never duplicated (FR-009). The request goes out with
  `trigger: "regenerate-message"`, which the contract allows.
- **Alternatives**: `sendMessage` with the same text (duplicates the bubble).

## R4 — Markdown rendering while streaming

- **Decision**: `streamdown` (v2) for assistant text.
- **Rationale**: built for AI streaming. `remend` closes incomplete markdown (unclosed `**`, half
  tables) so the layout does not flash; GFM tables; sanitization (`rehype-sanitize`) and
  `rehype-harden` link/image protocol allow-lists cover FR-002 (no raw HTML execution, no
  `javascript:` links). v2 keeps syntax highlighting/math/mermaid as opt-in plugins, so the core
  stays small. It is the renderer AI SDK UI examples use.
- **Alternatives**: `react-markdown` + `remark-gfm` (safe defaults, but shows raw `**` mid-stream
  and needs manual link hardening); AI Elements registry (pulls many components we don't need
  before the Figma pass). Exact props (`parseIncompleteMarkdown`, link safety options) are
  confirmed from `node_modules/streamdown` types at implementation time.

## R5 — Components and styling

- **Decision**: small hand-written chat components in `src/components/chat/` on top of shadcn
  primitives added with `pnpm dlx shadcn add` (`textarea`, `card`, `badge`, `alert`) on the
  existing `base-nova` style. Colours, radii and spacing only through the theme tokens in
  `globals.css` (FR-015) — no hard-coded hex values. Icons from `lucide-react` (already
  installed).
- **Rationale**: few components, full control of states and layout; branding (#18) changes
  tokens only.

## R6 — Copy catalog (pt-BR, PT/EN-ready)

- **Decision**: `src/lib/i18n/pt-BR.ts` exports a typed `messages` object (nested keys);
  `src/lib/i18n/index.ts` exports `t` helpers (`messages` getter + `format(key, vars)` for
  `{seconds}`-style interpolation). The type of the pt-BR object is the `Messages` shape an `en`
  catalog must satisfy in #13. Tool labels and availability labels live in the catalog; the tool
  table is copied verbatim from the contract and a unit test asserts every contract tool name has
  a label.
- **Alternatives**: `next-intl` now (routing/middleware for a feature we don't ship yet — YAGNI;
  #13 can adopt it and reuse the catalog shape).

## R7 — `/login` placeholder under Cache Components

- **Decision**: `src/app/login/page.tsx` server page rendering a static shell and a client
  `<LoginNotice/>` that reads `useSearchParams()` wrapped in `<Suspense>` (required: Next 16 docs,
  `use-search-params.md` § Prerendering). Redirect from the chat uses `useRouter().replace(...)`.
- **Alternatives**: reading `searchParams` in the server page (also needs a Suspense boundary
  under Cache Components; client hook is simpler to replace in #10).

## R8 — Component tests

- **Decision**: add `vitest.config.ts` (jsdom environment for `*.test.tsx`, `@/` alias,
  `setupFiles` with `@testing-library/jest-dom`), dev deps `jsdom`, `@testing-library/react`,
  `@testing-library/user-event`, `@testing-library/jest-dom`. Extract the fixture → `UIMessage`
  helpers of `contract.test.ts` into `src/test/fixtures.ts` and reuse them:
  - **Rendering tests** feed assembled `UIMessage`s to `<MessageView/>` (pure presentational).
  - **Flow tests** render `<Chat/>` with a stub `fetch` (passed to the transport) that returns
    the real fixture bodies/status codes, so `useChat` itself is exercised end to end with no
    server. `/fixture <name>` is not needed in tests.
- **Rationale**: no network, no API key (constitution IV); fixtures stay the single source.
- **Alternatives**: Playwright (that is #16); MSW (extra dependency for one endpoint).

## R9 — Accessibility and mobile

- **Decision**: `h-dvh` flex column layout (header / scrollable `role="log"` list / pinned
  input), `min-w-0` + `break-words` + `overflow-x-auto` on markdown tables/code; a visually hidden
  `aria-live="polite"` region announces each assistant message when it finishes (not per token).
  Tap targets ≥ 44 px (`size-11`). Stick-to-bottom scrolling: scroll to bottom on new content only
  when the user is within ~80 px of the bottom.
- **375 px check**: a component test asserts no element in the rendered fixtures has a
  fixed width greater than the viewport (layout classes), plus a manual check at 375 × 667
  recorded in the final PR; automation is #16.
