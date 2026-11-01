---

description: "Task list for 008 Figma branding (epic #18)"
---

# Tasks: Figma branding

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

- [ ] T006 Replace tokens in `frontend/src/app/globals.css` (paper, ink, rosewood, brass,
      bubbles, banners). Keep the Streamdown `@source`.
- [ ] T007 [P] Add `frontend/public/brand-mark.svg` and switch `frontend/src/app/layout.tsx`
      fonts to Fraunces + Figtree (do not add an i18n provider).
- [ ] T008 Restyle `frontend/src/components/chat/chat-header.tsx` with the mark (no Sign out,
      no PT/EN).
- [ ] T009 [P] Restyle `frontend/src/components/chat/empty-state.tsx` chips and greeting.
- [ ] T010 Restyle conversation: `chat.tsx` shell, `message-list.tsx`, `message-view.tsx`,
      `markdown.tsx` (hardening unchanged), `typing-indicator.tsx`.
- [ ] T011 [P] Restyle `tool-status.tsx` (keep `role="status"`) and `product-card.tsx` /
      `product-cards.tsx` (no photo; format only).
- [ ] T012 Restyle `chat-input.tsx` (targets ≥ 44 px) and `chat-error.tsx` banners.
- [ ] T013 Restyle the `/login` placeholder (`login/page.tsx`, `login-notice.tsx` classes only).
      No `login-form.tsx`.
- [ ] T014 Gate: `pnpm lint && pnpm typecheck && pnpm test && pnpm build` in `frontend/`.
      `/` and `/login` still prerender. Screenshots if a browser is available.

## Later (after #44 → #13 on `main`)

- [ ] T015 Rebase and restyle `login-form.tsx`, Sign out, language switch; do not invent catalog
      keys.

## Parallel opportunities

T006–T007 together; T009/T011 together after tokens; T014 last.
