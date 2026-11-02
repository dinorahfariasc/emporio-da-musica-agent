# Implementation Plan: Store home with a side chat widget

**Spec**: `specs/009-store-home/spec.md` · Part of #18 · Decision: DL-FE-004

## Approach

- **Route:** `src/lib/routes.ts` lists public pages (`/`). `src/proxy.ts` lets them through; every
  other page and `/api/chat` keep the existing guard. No change to auth logic.
- **Session in the widget:** `SessionProvider` + `useSession` (next-auth client) read
  `/api/auth/session`. Signed out: Melody intro + link to `/login?callbackUrl=%2F`. Signed in:
  the existing `Chat`. Detection is client-side, so `/` stays a static prerender.
- **Content:** `store` and `widget` blocks in `pt-BR.ts` / `en.ts`; contact facts (legal name,
  CNPJ, address, phone, WhatsApp, e-mail) in `src/lib/store-info.ts`, not translated.
- **Widget state:** `<html data-chat="open|closed">` set by a static inline script in `<head>`
  (like the theme), written on toggle to `melody-chat-desktop` / `melody-chat-mobile`. Tailwind
  `in-data-[chat=open]:` variants show the panel or the FAB, so the panel (and `useChat`) is
  always mounted and only hidden.
- **Layout:** chat components use container queries (`@3xl:` instead of `md:`) so the chat
  takes the phone layout inside the 400 px panel and the wide layout full-screen.
- **Accessibility:** panel is `complementary` on desktop and a modal `dialog` on mobile (page
  `inert`); Esc minimises; focus moves to the panel and back to the FAB.

- **Background (round 2):** `music-staff-background.tsx` renders static SVG (no client JS) in a
  fixed layer at `z-index:-1` inside the page wrapper (`isolate`), so header, cards and footer
  stay solid on top and the chat panel/FAB (outside the wrapper) are never covered; the layer
  stops at the panel edge when it is open. Lines and notes share one sine wave in a 1440 × 900
  box, so notes sit on the lines at any size. A horizontal mask (≤ 60 %, 40 % in the centre)
  keeps text contrast. Styles and the float keyframes in `globals.css` (`.staff-bg`).
- **Hovers (round 2):** `.store-card` / `.store-card-icon` in `globals.css`; hover only inside
  `@media (hover: hover)`, plus `:focus-within`; reduced motion removes the lift.

- **Round 3:** the init script defaults to `open` on both layouts. Maximised is React state in the
  controller (desktop only), mirrored to `<html data-chat-max>` for the scroll lock; the panel
  swaps its side-panel classes for full-window ones and its role to a modal dialog, and the page
  wrapper becomes `inert` (keeps focus in the chat). Same DOM node, so `useChat` is not remounted.

## Files

- New: `src/components/store/{store-shell,store-header,store-sections,store-footer,chat-widget,
  use-chat-widget,sections}.ts(x)`, `src/lib/{routes,chat-widget,store-info}.ts`, tests.
- Changed: `src/app/page.tsx`, `src/app/layout.tsx`, `src/app/globals.css`, `src/proxy.ts`,
  `src/components/chat/{chat,chat-view,chat-input,empty-state,message-list,product-cards}.tsx`,
  `src/lib/i18n/{pt-BR,en}.ts`, DEV gallery (`frame=widget`, `widget-signin`).
