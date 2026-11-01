# Prompt for the UI agent (frontend, Figma branding)

You are building the UI of the Empório da Música chat (Melody, a customer-service agent for a
music store). The Figma file is ready; apply it to the existing Next.js app **without changing
behaviour**. Final delivery deadline: 2026-11-02 18:00 (America/Campo_Grande); the repo cannot
change after that. Work in small PRs.

## Read first
1. `docs/HANDOFF.md` (status, environment, gotchas) and `CLAUDE.md` (rules).
2. `docs/design/figma-brief.md` (screens, chat anatomy, states, constraints). The Figma link is
   provided by the user.
3. `specs/003-chat-web/spec.md` and `docs/contracts/chat-stream.md` (what the UI renders).
4. `frontend/node_modules/next/dist/docs` before using any Next API: Next 16 with Cache
   Components, ai@7, @ai-sdk/react@4, Vitest 5, Tailwind. These are newer than most docs.

## Rules
- Spec-driven: write a short spec/plan/tasks for the branding epic (#18) under `specs/` (next
  free number; 004-007 are taken) before the code.
- English for code, docs, commits, PRs. UI copy is pt-BR first with EN via the i18n catalog.
- Semantic commits (`feat:`, `fix:`, `docs:`, `test:`). **No mention of AI/Claude and no
  Co-Authored-By trailers**, even if a tool's default adds them. Do not push or open PRs without
  asking the user; the user merges.
- Decision-log entries use the per-area id `DL-FE-NNN` (check the highest existing DL-FE; do not
  use sequential DL-NNN).
- pnpm only. Gate per PR: `pnpm lint && pnpm typecheck && pnpm test && pnpm build`; `/` and
  `/login` must still prerender.

## Work in parallel with other agents: avoid conflicts
Other work in flight touches the same frontend files. Until it lands, restrict yourself to:
- **Allowed now:** design tokens in `src/app/globals.css`, the Tailwind theme, fonts, logo and
  static assets in `public/`, new presentational components under `src/components/ui/`.
- **Wait for the merge, then rebase on `main`, before editing:** `src/app/login/page.tsx`,
  `src/components/login/login-form.tsx`, `src/components/chat/chat-header.tsx`,
  `src/components/chat/product-card.tsx`, `src/app/layout.tsx`, `src/lib/i18n/*`. Merge order:
  **#44 (auth) -> #13 (PT/EN switch) -> your branding PRs.** Ask the user whether both merged
  (`gh pr list --state merged`) before touching them.
- **Never touch:** `frontend/auth.ts`, `src/lib/auth/*`, `src/proxy.ts`, `src/app/api/**`,
  `scripts/create-user.ts`, `src/lib/chat/*` (stream logic, tool labels), and anything under
  `backend/`. Restyle; never re-wire behaviour.

## Constraints that must survive the restyle
- 375 px with no horizontal scroll; tap targets >= 44 px; iOS safe-area insets.
- `role="status"` announcements for tool state; visible focus; AA contrast.
- Markdown images stay blocked; links stay allow-listed; product cards have **no image** (the
  data has none), so the card must look right without one.
- Prices, discounts and availability are only formatted, never computed (constitution I). Format
  `R$ 1.234,56`.
- No status codes, error codes, JSON or tool names ever shown to the customer.
- Every string goes through the i18n catalog; no hard-coded text in components.
- The distinct states of spec 003 US3 (401, 429 rate-limited with countdown, 429 budget
  exhausted, 500 retry, dropped stream) must keep working and look designed.

## Suggested order
1. Spec/plan/tasks for #18 (short).
2. Tokens, fonts, logo (no overlap with other branches).
3. Chat surface: bubbles, typing indicator, tool status line, input, Stop button, empty state
   and suggestion chips.
4. Product card.
5. Error and limit banners.
6. Header and login page (after the merge order above).
7. Mobile and dark-mode pass (if the Figma has it), then audits (axe, Lighthouse, 375 px
   screenshot for the README).

## Done means
Lint, typecheck, tests and build green; mock fixtures (`/fixture <name>`) all render in the new
style at 375 px and desktop; HANDOFF session-log entry added; PR description lists screenshots.
