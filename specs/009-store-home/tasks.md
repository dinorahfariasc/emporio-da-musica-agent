# Tasks: Store home with a side chat widget

Part of #18 · Spec `specs/009-store-home/spec.md`

- [x] T001 Public `/` in `src/proxy.ts` via `src/lib/routes.ts` (+ test)
- [x] T002 PT/EN catalog blocks `store` and `widget` from manual v2.1 (public sections only)
- [x] T003 `store-info.ts` with legal name, CNPJ, address, phone and WhatsApp as separate channels, e-mail
- [x] T004 Store header (anchors menu, PT | EN, theme, Entrar/Sair), sections, footer
- [x] T005 Chat widget: side panel ≥ 1024 px, FAB, mobile sheet, Esc, focus, unread dot
- [x] T006 No-flash widget state script + localStorage per layout
- [x] T007 Chat components on container queries; `ChatView` `embedded` / `header` props
- [x] T008 DEV gallery: `frame=widget` and `widget-signin`
- [x] T009 Tests: widget open/minimise/persistence, FAB a11y, signed-out prompt, i18n parity
- [x] T010 DL-FE-004, HANDOFF
- [x] T011 Gate green; screenshots 375/1440 light/dark in `emporio-design-ref/shots/store/`
- [x] T013 Music staff background (own SVG notes, float animation, reduced motion, AA kept) + test
- [x] T014 Card hovers / focus-within on key info cards; hero CTA, chips and contact links hover/active
- [x] T015 Section menu wraps instead of cutting off next to the open panel; e-mail wraps after "@"
- [x] T016 Screenshots round 2 in `emporio-design-ref/shots/store2/`
- [x] T017 Open by default on mobile too (saved choice wins); maximise/restore on desktop + tests
- [x] T018 Review of #59: minimised by default on mobile (round 4); catalog copy matches the data; "da Empório" everywhere; backend aligned with DL-FE-005
- [x] T018 Screenshots round 3 in `emporio-design-ref/shots/store3/`
- [x] T012 E-mail without accent and minimum instalment R$ 100,00 decided by Dinorah (DL-FE-005)
- [ ] T019 Store confirms the DL-FE-005 assumptions
