# Implementation Plan: Chat web

**Branch**: `dinorahfariasc/chat-web` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-chat-web/spec.md` · Epic #9

## Summary

A full-page chat for Melody at `/` in the existing Next.js app (`frontend/`). `useChat` from
`@ai-sdk/react` consumes the #4 UI message stream through the existing `POST /api/chat` route
(mock mode replays the contract fixtures; production fails closed to the backend). Assistant text
is rendered with a hardened Streamdown (no images, allow-listed links, no raw HTML), tool parts
become pt-BR status lines, `data-products` parts become basic product cards, and errors are
mapped by one pure function onto the contract's error-code table (401 → `/login` placeholder,
429 rate/budget → disabled input, 500/stream errors/dropped streams → retry). All copy lives in a
typed pt-BR catalog read through `useMessages()`. Tests drive the real `useChat` with a stub `fetch` that serves the fixture files.

## Technical Context

**Language/Version**: TypeScript 5, React 19.3, Node 24

**Primary Dependencies**: Next.js 16.4 (App Router, Cache Components on), `ai@7`,
`@ai-sdk/react@4`, Tailwind v4, shadcn/ui (`base-nova`, `@base-ui/react`), `lucide-react`;
**new**: `streamdown` (runtime); `jsdom`, `@testing-library/react`, `@testing-library/user-event`,
`@testing-library/jest-dom` (dev)

**Storage**: N/A (in-memory `useChat` state per page session)

**Testing**: vitest 5 (`pnpm test`, in CI) — jsdom for component tests; fixtures from
`contracts/chat-stream/fixtures/`

**Target Platform**: modern evergreen browsers, mobile ≥ 375 px; deployed on Vercel (#10)

**Project Type**: web application (frontend part of the monorepo)

**Performance Goals**: user bubble + typing indicator < 100 ms after send (SC-003); incremental
text rendering without jank (SDK throttling, Streamdown memoized blocks)

**Constraints**: no backend/API key in dev and CI; no UI computation of prices/stock/discounts;
no PII in console; markdown never renders or requests images; Cache Components rules
(`useSearchParams` under `<Suspense>`, no `export const dynamic`, no random ids read during
render)

**Scale/Scope**: 2 routes (`/`, `/login`), ~9 chat components, 1 catalog, 4 SSE + 4 HTTP fixtures

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Facts from the system | Cards display `ProductCard` values as sent; only `Intl` formatting. No price/discount/stock logic in UI (FR-005). Test asserts card values equal fixture values (SC-008). | ✅ |
| II. LLM only where it adds value | No LLM in the frontend; metadata not used. | ✅ N/A |
| III. Clean, traceable data | Reads the shared contract fixtures; no data transformation. | ✅ N/A |
| IV. Tested before done | Fixture rendering + every error state tested with no network/API key; contract test kept; bug fixes require regression tests. | ✅ |
| V. Safe and respectful | Hardened Streamdown: no raw HTML, no images (blocks PII exfiltration via image URLs), links only `https/http/mailto` (FR-002, research R4); no message/PII logging (FR-017); 401 → login; mock never served in production by default (FR-011). Auth/limits enforcement stays server-side (#10). | ✅ |
| VI. Simple, modular, replaceable | Reuses route + mock; one runtime dep (Streamdown) justified in research R4; test deps justified in R8; no i18n framework yet (R6). | ✅ |
| Language policy | Code/docs in English; UI copy pt-BR in one catalog. | ✅ |

**Post-design re-check (after Phase 1)**: unchanged — all pass, no Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/003-chat-web/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions R1–R9
├── data-model.md        # Phase 1 — message/part/product/error/catalog shapes
├── quickstart.md        # Phase 1 — run + manual validation
├── contracts/
│   └── ui-rendering.md  # Phase 1 — fixture → expected UI, component interfaces
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
contracts/chat-stream/fixtures/        # from #4 (read-only here)
frontend/
├── vitest.config.ts                   # new: jsdom for *.test.tsx, @/ alias, setup file
├── src/
│   ├── app/
│   │   ├── layout.tsx                 # <html lang={locale}>, viewport export
│   │   ├── globals.css                # + @source for streamdown dist
│   │   ├── page.tsx                   # replaced: renders <Chat/>
│   │   ├── login/page.tsx             # new: placeholder + <Suspense><LoginNotice/></Suspense>
│   │   └── api/chat/route.ts          # existing; uses chatMode() (fail closed in production)
│   ├── components/
│   │   ├── ui/                        # shadcn: button (exists), textarea, card, badge, alert
│   │   ├── chat/
│   │   │   ├── chat.tsx               # client; owns useChat, error/redirect/countdown logic
│   │   │   ├── chat-header.tsx
│   │   │   ├── message-list.tsx       # role="log", stick-to-bottom, live region
│   │   │   ├── message-view.tsx       # pure: parts → components
│   │   │   ├── markdown.tsx           # Streamdown wrapper
│   │   │   ├── tool-status.tsx
│   │   │   ├── product-cards.tsx      # grid
│   │   │   ├── product-card.tsx       # single card (#20 restyles this)
│   │   │   ├── chat-input.tsx
│   │   │   ├── chat-error.tsx
│   │   │   ├── typing-indicator.tsx
│   │   │   └── empty-state.tsx
│   │   └── login/login-notice.tsx     # client; reads ?reason
│   ├── lib/
│   │   ├── chat/
│   │   │   ├── types.ts               # ChatMessage, ProductCard, ChatMetadata
│   │   │   ├── errors.ts              # toChatError (pure)
│   │   │   ├── tool-state.ts          # SDK state → ToolDisplayState
│   │   │   ├── mode.ts                # chatMode(): CHAT_MODE ?? (production ? backend : mock)
│   │   │   ├── mock.ts                # existing
│   │   │   └── contract.test.ts       # existing; uses src/test/fixtures.ts
│   │   ├── format.ts                  # formatBrl(value, locale), formatPercent
│   │   └── i18n/
│   │       ├── pt-BR.ts               # catalog (source of the Messages type)
│   │       └── index.tsx              # locale, useMessages(), getMessages(), format()
│   └── test/
│       ├── setup.ts                   # jest-dom matchers
│       └── fixtures.ts                # read fixtures, assemble UIMessage, stub fetch (sequence, truncate)
```

**Structure Decision**: single frontend package (`frontend/`) of the existing monorepo. Pure
logic (`lib/`) is unit-tested in the node environment; components are tested in jsdom next to
their source (`*.test.tsx`).

## Delivery slices (3 PRs, cut after review)

1. **PR 1 — Foundation + US1** (`Part of #9`): test setup, fixtures helper, types, catalog +
   `useMessages`, formatters, `toChatError`, tool-state, `chatMode()` fail-closed, hardened
   Markdown, chat page with streaming, input, stop, empty state, typing indicator, double-send
   guard, dropped-stream detection. `pnpm build` run early to catch Cache Components issues.
2. **PR 2 — US2 + US3** (`Part of #9`): tool status, product cards, all error states, retry,
   countdown, budget lock, `/login` placeholder.
3. **PR 3 — US4 + polish** (`Closes #9`): 375 px layout and a11y fixes, copy/colour audit, manual
   quickstart with screenshot, DL-009 update.

Cut by the review (deadline): class-name layout test (manual 375 px check instead), login-notice
test, markdown-table parsing in the tool-label test (const list instead), pending-fetch helper and
the 100 ms test, the 1,800-char counter (`maxLength` only), the separate decision-log task.

## Risks

| Risk | Mitigation |
|---|---|
| ai@7 / Next 16 APIs differ from docs | Verified in `node_modules` (research); re-check types before each slice |
| Streamdown prop names differ in v2 | Verified in 2.7.1 `.d.ts` (`rehypePlugins`, `components`, `controls`, `translations`, `mode`); fall back to `react-markdown` + `remark-gfm` with `urlTransform` if it blocks |
| jsdom lacks `ReadableStream`/`TextDecoderStream` | Node 24 globals are available in vitest jsdom; polyfill in `setup.ts` if needed |
| Mock served in production if `CHAT_MODE` is unset | Fixed here: `chatMode()` fails closed to `backend` in production (R11) |
| Streamdown defaults allow any image/link (PII exfiltration) | Hardened config + `img → null` + hostile-markdown test (R4) |
| Fake timers stall streams in tests | Fake only `setInterval`; `userEvent` with `advanceTimers` (R8) |
| Prerender error from random ids during render | Never read `chat.id` in render; build in PR 1 (R10) |

## Complexity Tracking

No violations.
