---

description: "Task list for 008 Figma branding (epic #18)"
---

# Tasks: Figma branding

> Palette: the approved Melody UI (DL-FE-002) replaced the fallback palette from DL-FE-001.
> T006–T014 landed on `feat/ui-melody`; screenshots are outside the repo.

**Input**: [spec.md](spec.md), [plan.md](plan.md), `docs/design/figma-brief.md`

**Tests**: existing 003 fixture tests must stay green. Do not add colour assertions.

## PR 1 — Spec and notes (`Part of #18`)

- [x] T001 Create `specs/008-figma-branding/{spec,plan,tasks}.md`
- [x] T002 Append `DL-FE-001` to `docs/decision-log.md`
- [x] T003 Update `docs/HANDOFF.md` §3, §3b and the session log
- [x] T004 Point S13/#18 in `docs/planning/backlog.md` at this spec
- [x] T005 [P] Note in `specs/003-chat-web/spec.md` (FR-015, assumptions), `plan.md`,
      `contracts/ui-rendering.md`, `quickstart.md` and `tasks.md` that branding is 008

## PR 2 — Tokens + current surfaces (`Part of #18` / `Closes #18` if this slice finishes)

- [x] T006 Replace tokens in `frontend/src/app/globals.css` with the approved palette (DL-FE-002;
      Inter, action `#E00B41`, light + dark). Keep the Streamdown `@source`.
- [x] T007 [P] ~~Add `frontend/public/brand-mark.svg`~~ and switch `frontend/src/app/layout.tsx`
      fonts. Superseded by DL-FE-002: the SVG was deleted; the mark is the `BrandMark`
      component in `src/components/ui/brand-mark.tsx`, and the font is Inter. `layout.tsx` now
      wraps the app in `LocaleProvider` (approved PT | EN screens).
- [x] T008 Restyle `frontend/src/components/chat/chat-header.tsx` with the mark (Sign out and
      PT | EN included on `feat/ui-melody`, per the approved screens).
- [x] T009 [P] Restyle `frontend/src/components/chat/empty-state.tsx` chips and greeting.
- [x] T010 Restyle conversation: `chat.tsx` shell, `message-list.tsx`, `message-view.tsx`,
      `markdown.tsx` (hardening unchanged), `typing-indicator.tsx`.
- [x] T011 [P] Restyle `tool-status.tsx` (keep `role="status"`) and `product-card.tsx` /
      `product-cards.tsx` (no photo; format only).
- [x] T012 Restyle `chat-input.tsx` (targets ≥ 44 px) and `chat-error.tsx` banners.
- [x] T013 Restyle `/login` (`login/page.tsx`, `login-notice.tsx`, and `login-form.tsx`, which
      already exists on this branch).
- [x] T014 Gate: `pnpm lint && pnpm typecheck && pnpm test && pnpm build` in `frontend/`.
      `/` and `/login` still prerender. Screenshots if a browser is available.

## Later (after #44 → #13 on `main`)

- [ ] T015 Rebase onto `main` after #44 → #13 and reconcile `en.ts`, `lib/i18n/context.tsx` and
      `language-switch.tsx` with #13 (restyle already done on `feat/ui-melody`).

## Parallel opportunities

T006–T007 together; T009/T011 together after tokens; T014 last.
