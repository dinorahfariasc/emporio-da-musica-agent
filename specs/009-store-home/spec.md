# Feature Specification: Store home with a side chat widget

**Feature Branch**: `feat/store-home`

**Created**: 2026-11-01

**Status**: Draft

**Input**: Turn the chat-only front into the store's home page. `/` shows public store
information (about, hours, address and contact, payment, returns, shipping, promotions,
warranty, privacy) taken from the store manual v2.1 (`challenge/` PDF). Melody moves into a
side widget that can be minimised to a floating button.

Part of #18.

## Clarifications

- **Content source:** store manual v2.1, public sections only (§1, §1.1, §1.2, §2, §3, §4, §5,
  §6.1, §8, §9). Internal guidance (§7 tone/flow/special situations, §10) and the internal
  tracking-code format are not published. Numbers, deadlines and prices are copied, never
  computed.
- **Phone and WhatsApp are separate channels:** "Telefone (ligações): (67) 3341-4444"
  (`tel:+556733414444`) and "WhatsApp (mensagens): (67) 3321-4500"
  (`https://wa.me/556733214500`), in the contact section and in the footer.
- **E-mail:** the cover spelling `contato@emporiodamusica.com.br` (no accent); see Assumptions.
- **Auth unchanged:** only `src/proxy.ts` learns that `/` is public. `/api/chat` stays protected;
  `auth.ts`, `src/lib/auth/*`, lockout, create-user and the backend are not touched.

- **2026-11-01 — round 2 (Dinorah):** "more of a music store": a background of notes floating over
  a staff, and hovers on the key information cards. The reference attachment did not arrive, so
  the style is our own (FR-010, FR-011).

- **2026-11-01 — round 3 (Dinorah):** "Melody must already be open when the page opens, and add an
  option to maximise the window." Open by default on mobile too (FR-007); maximise (FR-013).

## Assumptions

Decided by Dinorah on 2026-11-02, **to be confirmed by the store** (DL-FE-005):

- **E-mail without accent.** The manual has `contato@emporiodamusica.com.br` on the cover and an
  accented spelling in the body. The page shows only the unaccented address.
- **Minimum instalment R$ 100,00.** The card table in §3 says "parcela mínima de R$ 100,00"; §3.1
  says R$ 80,00 for 4x–6x. The page uses R$ 100,00 for 4x–6x too; every other §3.1 condition is
  unchanged (up to 3x, 7x–12x, combined payment over R$ 2.000,00).
- **Phone and WhatsApp are different channels:** calls (67) 3341-4444, messages (67) 3321-4500.

## User stories

1. **Visitor without an account (P1).** Opens `/`, reads the store information in PT or EN and
   sees Melody's intro with "Entrar para conversar", which goes to `/login` and back to `/`.
2. **Signed-in customer (P1).** Chats with Melody in the widget exactly as before (streaming,
   tools, cards, 429, budget, errors) while reading the page.
3. **Minimise (P1).** Minimises the chat to a floating button without losing the conversation or
   an in-flight answer; a dot on the button flags a new answer that arrived while minimised.

## Requirements

- **FR-001** `/` is public and prerendered (static). `/login` unchanged. Gallery DEV-only.
- **FR-002** Sections with anchors and header menu entries: Início, Quem somos, Horário,
  Endereço e contato, Pagamento, Trocas e devoluções, Frete, Promoções, Garantia, Privacidade;
  footer with legal name, CNPJ, contact and section links.
- **FR-003** All copy through the i18n catalog, PT and EN with key parity.
- **FR-004** Desktop (≥ 1024 px): fixed right panel (380–400 px), nearly full height, Melody header
  with a minimise button; the page reserves padding on the right so content is never covered.
- **FR-005** Minimised: floating action button bottom-right, brand icon, catalog aria-label,
  ≥ 44 px, visible focus, unread dot.
- **FR-006** Mobile (< 1024 px): the FAB opens a full-screen sheet (dialog, page behind inert)
  with a close control.
- **FR-007** State in localStorage per layout; with no saved choice the chat starts open on desktop
  and on mobile (full-screen sheet with a visible minimise control); a saved "minimised" wins. Set
  before first paint (no flash).
- **FR-008** `useChat` stays mounted while minimised. Esc minimises; focus goes to the panel on
  open and back to the FAB on minimise; no focus trap on the desktop side panel.
- **FR-009** 375 px without horizontal scroll, tap targets ≥ 44 px, AA contrast, safe areas, light
  and dark themes, approved tokens, no stock images.

- **FR-010** Decorative background: faint waving five-line staves with 10–16 own SVG notes (♪ ♫ ♩,
  treble clef) floating slowly (transform only, 6–12 s, out of step). Token colours at low
  opacity, masked behind the content; text keeps AA in light and dark. `aria-hidden`, no pointer
  events, behind the page, never under the chat panel or FAB, no overflow at 375 px, still with
  `prefers-reduced-motion`.
- **FR-011** Key info cards lift slightly (−3 px), take the larger elevation token and an accent
  edge on hover (pointer devices only) and on `:focus-within`; icons tint/scale. 150–200 ms,
  none with reduced motion. Non-clickable cards keep the default cursor.
- **FR-012** The section menu never cuts off (wraps to a second row next to the open panel);
  the e-mail wraps after "@" on narrow screens.

- **FR-013** Desktop: a maximise/restore button (Maximize2/Minimize2) next to minimise turns the panel
  into a full-window overlay (modal dialog, page inert, body scroll locked, chat in its ≤ 760 px
  reading column). Esc restores, then minimises. Same chat instance (no restart). Not saved:
  a reload shows the side panel. Hidden below 1024 px (already full screen). Labels from the
  catalog; ≥ 44 px; fade only with `prefers-reduced-motion: no-preference`.

## Success criteria

- Gate green (`pnpm lint && pnpm typecheck && pnpm test && pnpm build`), `/` and `/login` static.
- Tests: widget open/minimise/persistence, FAB accessibility, i18n parity, signed-out prompt.
- Screenshots at 375 and 1440 px, light and dark, reviewed.
