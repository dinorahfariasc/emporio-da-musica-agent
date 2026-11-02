# Feature Specification: Figma branding (Chat Melody UI)

**Feature Branch**: `008-figma-branding`

**Created**: 2026-11-01

**Status**: Draft

**Input**: Apply the Chat Melody Figma branding to the existing Next.js chat without changing
behaviour. Epic #18 (S13). Screens and states: `docs/design/figma-brief.md`. Implementation
constraints: `docs/design/ui-agent-prompt.md`. Behaviour stays `specs/003-chat-web` +
`docs/contracts/chat-stream.md`.

**Epic**: #18 · **Depends on**: #9 (003 chat web, merged) · **Waits for restyle of auth chrome**:
#10 / #44 (login form, sign out) and #13 (PT/EN catalog + switch) · **Related**: #20 (polished
product cards, absorbed here)

## Clarifications

- **2026-11-01 — approved palette (DL-FE-002).** The approved Melody UI (Inter, action `#E00B41`,
  brand `#FF385C` for the mark only, light + dark tokens) replaces the fallback palette below.
  `public/brand-mark.svg` was deleted; the mark is the `BrandMark` component. On `feat/ui-melody`
  the login form, Sign out and PT | EN (with `en.ts`) are styled too, because the approved screens
  include them; reconcile with #13 when it lands. Mentions of cream paper, rosewood, brass,
  Fraunces or the SVG mark below are historical.
- The Figma MCP was rate-limited on 2026-11-01. Tokens and frames come from the brief plus a
  store-brand theme (warm paper, rosewood, brass) until the file can be re-read. Re-open
  https://www.figma.com/design/ReQoFKg7YK90YmqsSNbfTU/Empório-da-Música-—-Chat-Melody--UI-?node-id=0-1
  when quota allows and align tokens if they diverge.
- Restyle only. No new routes, no stream/auth/i18n wiring, no price/stock/discount math.
- Login form, PT/EN switch and Sign out land after #44 and #13 merge; this epic restyles the
  surfaces that exist on `main` (placeholder `/login`, header without those controls).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Melody's store brand on the chat (Priority: P1)

A customer opens `/` and `/login` and immediately recognises Empório da Música: cream paper
background, rosewood/brass tokens, store mark, Fraunces headings, branded bubbles, chips, cards
and error banners. Sending a message, watching tools, reading product cards and recovering from
errors still works exactly as in 003.

**Why this priority**: #18 is the visual delivery; the evaluator judges the store, not shadcn defaults.

**Independent Test**: replay every 003 fixture on the mock; behaviour matches
`specs/003-chat-web/contracts/ui-rendering.md`; 375 px has no horizontal scroll; tokens come from
`globals.css` / the brand mark, not hardcoded hex in every component.

**Acceptance Scenarios**:

1. **Given** the empty chat, **When** `/` loads, **Then** the header shows the store mark plus
   Melody's name and tagline, the greeting and suggestion chips use the brand type and chip style,
   and no new copy is hardcoded in JSX.
2. **Given** a conversation (`plain-text`, `tool-products`, `tool-error`), **When** fixtures replay,
   **Then** user bubbles, Melody bubbles, the typing indicator, tool status lines and product
   cards use the brand tokens; cards have no product photo (colour/icon block is allowed).
3. **Given** 429 rate, 429 budget, 500/retry and dropped-stream states, **When** those fixtures
   replay, **Then** each remains a distinct recovery state (003 US3) and uses the designed banner
   style; no status codes, JSON or tool names appear.
4. **Given** the placeholder `/login`, **When** the page opens (and when `?reason=expired`),
   **Then** it uses the same tokens and mark; the session-expired notice and back link still work.
5. **Given** a 375 px viewport, **When** any fixture is shown, **Then** there is no horizontal
   page scroll, tap targets stay ≥ 44 px, and safe-area insets remain.

---

### User Story 2 - Auth and language chrome after #44 and #13 (Priority: P2)

After those PRs merge, the real login form, lockout copy, Sign out and the PT/EN switch pick up
the same tokens. Out of scope for the first implementation slice.

**Why this priority**: those files are owned by in-flight PRs; restyling them on `main` now
conflicts and would be overwritten.

**Independent Test**: after rebase onto `main` that contains #44 and #13, the form/switch/sign-out
render with brand tokens and existing behaviour.

**Acceptance Scenarios**:

1. **Given** #44 and #13 on `main`, **When** the branding branch rebases, **Then** login fields,
   generic/lockout errors, Sign out and PT | EN use the Figma tokens without new hardcoded copy.

---

### Edge Cases

- Dark mode: ship a coherent dark token set (espresso/brass). Align to Figma frames if the file
  has them; otherwise keep AA contrast.
- `#44` / `#13` merge conflicts on `login/page.tsx`, `chat-header.tsx`, `layout.tsx`, `product-card.tsx`:
  rebase and keep behaviour from those PRs, visuals from this epic.
- Product `categoryId` may tint a colour block; that is presentation, not a computed fact.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Design tokens (colour, radius, type, spacing) MUST live in `frontend/src/app/globals.css`
  (and the logo under `frontend/public/`). Components consume tokens/utilities, not one-off hex
  palettes that bypass the theme.
- **FR-002**: Behaviour of 003 FR-001–FR-019 MUST stay unchanged: stream, stop, tools, cards,
  errors, mock, fail-closed, markdown hardening, i18n hook.
- **FR-003**: No customer-facing string MAY be added outside the i18n catalog. This epic MUST NOT
  invent catalog keys or an `en.ts` (that is #13).
- **FR-004**: Product cards MUST stay image-less (contract has no image). A category colour block
  or icon is allowed. Prices/discounts/availability are formatted only.
- **FR-005**: 375 px, tap targets ≥ 44 px, safe-area, `role="status"` for tools, visible focus,
  contrast AA MUST survive the restyle.
- **FR-006**: `/` and `/login` MUST still prerender (Cache Components; no `export const dynamic`).
- **FR-007**: Lint, typecheck, tests and production build MUST pass. Fixture tests stay green
  without asserting colours.
- **FR-008**: Files that wire auth or the stream (`auth.ts`, `src/lib/auth/*`, `src/proxy.ts`,
  `src/app/api/**`, `src/lib/chat/**`, `backend/**`) MUST NOT be edited.
- **FR-009**: Login form, Sign out and PT/EN controls MUST NOT be added on `main` before #44/#13.
  The current header and login placeholder MAY be restyled.

### Key Entities

- **Brand tokens**: CSS variables from the approved Melody UI (DL-FE-002): surfaces, text, action,
  brand, bubbles, status banners; light and dark.
- **Store mark**: `BrandMark` component (brand tile + music icon) in the header and on `/login`.
- **Surfaces**: empty chat, conversation, tool line, product card, input, error banners, header,
  login placeholder.

## Success Criteria *(mandatory)*

- **SC-001**: 003 fixture tests remain green (behaviour).
- **SC-002**: A reviewer can tell `/` and `/login` apart from stock shadcn at 375 px and desktop.
- **SC-003**: Gate `pnpm lint && pnpm typecheck && pnpm test && pnpm build` is green.
- **SC-004**: Decision log has `DL-FE-001`; HANDOFF §3b lists what landed and what waits on #44/#13.

## Assumptions

- Source of visual screens: `docs/design/figma-brief.md`. Source of behaviour: 003 + chat-stream.
- Feature number 008: 004–007 are reserved (#10 auth, #21 admin, #14 HITL, and the prompt's hold).
- #20 polished cards are delivered by this epic's card restyle.
