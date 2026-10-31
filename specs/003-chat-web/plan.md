# Implementation Plan: Chat web

**Branch**: `dinorahfariasc/chat-web` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-chat-web/spec.md` · Epic #9

## Summary

A full-page chat for Melody at `/` in the existing Next.js app (`frontend/`). `useChat` from
`@ai-sdk/react` consumes the #4 UI message stream through the existing `POST /api/chat` route
(mock mode replays the contract fixtures). Assistant text is rendered with Streamdown, tool parts
become pt-BR status lines, `data-products` parts become basic product cards, and errors are
mapped by one pure function onto the contract's error-code table (401 → `/login` placeholder,
429 rate/budget → disabled input, 500/stream errors → retry). All copy lives in a typed pt-BR
catalog. Tests drive the real `useChat` with a stub `fetch` that serves the fixture files.

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
no PII in console; Cache Components rules (`useSearchParams` under `<Suspense>`, no
`export const dynamic`)

**Scale/Scope**: 2 routes (`/`, `/login`), ~9 chat components, 1 catalog, 4 SSE + 4 HTTP fixtures

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Facts from the system | Cards display `ProductCard` values as sent; only `Intl` formatting. No price/discount/stock logic in UI (FR-005). Test asserts card values equal fixture values (SC-008). | ✅ |
| II. LLM only where it adds value | No LLM in the frontend; metadata not used. | ✅ N/A |
| III. Clean, traceable data | Reads the shared contract fixtures; no data transformation. | ✅ N/A |
| IV. Tested before done | Fixture rendering + every error state tested with no network/API key; contract test kept; bug fixes require regression tests. | ✅ |
| V. Safe and respectful | Sanitized markdown, hardened links (FR-002); no message/PII logging (FR-017); 401 → login. Auth/limits enforcement stays server-side (#10). | ✅ |
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
│   │   ├── page.tsx                   # replaced: renders <Chat/>
│   │   ├── login/page.tsx             # new: placeholder + <Suspense><LoginNotice/></Suspense>
│   │   └── api/chat/route.ts          # existing (unchanged)
│   ├── components/
│   │   ├── ui/                        # shadcn: button (exists), textarea, card, badge, alert
│   │   ├── chat/
│   │   │   ├── chat.tsx               # client; owns useChat, error/redirect/countdown logic
│   │   │   ├── chat-header.tsx
│   │   │   ├── message-list.tsx       # role="log", stick-to-bottom, live region
│   │   │   ├── message-view.tsx       # pure: parts → components
│   │   │   ├── markdown.tsx           # Streamdown wrapper
│   │   │   ├── tool-status.tsx
│   │   │   ├── product-cards.tsx
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
│   │   │   ├── mock.ts                # existing
│   │   │   └── contract.test.ts       # existing; uses src/test/fixtures.ts
│   │   ├── format.ts                  # formatBrl, formatPercent
│   │   └── i18n/
│   │       ├── pt-BR.ts               # catalog (source of the Messages type)
│   │       └── index.ts               # messages, format(template, vars)
│   └── test/
│       ├── setup.ts                   # jest-dom matchers
│       └── fixtures.ts                # read fixtures, parse chunks, assemble UIMessage, stub fetch
```

**Structure Decision**: single frontend package (`frontend/`) of the existing monorepo. Pure
logic (`lib/`) is unit-tested in the node environment; components are tested in jsdom next to
their source (`*.test.tsx`).

## Delivery slices (small PRs)

1. **Foundation** — test setup (jsdom, fixtures helper, refactor `contract.test.ts` to use it),
   types, catalog, formatters, `toChatError`, tool-state mapping, shadcn primitives. Pure-logic
   tests. `Part of #9`.
2. **US1** — chat page, `useChat`, message list, Streamdown, input (Enter/Shift+Enter/stop/limit),
   empty state, typing indicator. Tests: `plain-text`, sanitization, input behaviour.
3. **US2** — tool status + product cards. Tests: `tool-products`, `tool-error`, unknown tool,
   empty products.
4. **US3** — error states, countdown, budget lock, retry, `/login` placeholder. Tests: four
   `http-*` fixtures + `stream-error`.
5. **US4 + polish** — 375 px layout, a11y (live region, focus, 44 px), copy audit, decision-log
   entry, quickstart run recorded. `Closes #9`.

## Risks

| Risk | Mitigation |
|---|---|
| ai@7 / Next 16 APIs differ from docs | Verified in `node_modules` (research); re-check types before each slice |
| Streamdown prop names differ in v2 | Confirm from its `.d.ts` in slice 2; fall back to `react-markdown` + `remark-gfm` with `urlTransform` if it blocks |
| jsdom lacks `ReadableStream`/`TextDecoderStream` | Node 24 globals are available in vitest jsdom; polyfill in `setup.ts` if needed |
| Mock defaults to `CHAT_MODE=mock` in prod | Out of scope; flagged for #10 |

## Complexity Tracking

No violations.
