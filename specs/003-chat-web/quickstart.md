# Quickstart: validate Chat web (003)

## Prerequisites

- Node 24, pnpm (version pinned in `frontend/package.json`).
- No backend, database or API key needed: the chat runs in mock mode.

## Setup

```bash
cd frontend
pnpm install --frozen-lockfile
cp .env.example .env.local   # CHAT_MODE=mock
pnpm dev                     # http://localhost:3000
```

## Automated checks (same as CI)

```bash
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

Expected: all green. `pnpm test` includes the contract test (#4) plus the fixture rendering and
error-state tests listed in [contracts/ui-rendering.md](contracts/ui-rendering.md).

## Manual scenarios (mock)

Send each message in the chat input. In mock mode the message text selects the fixture.

| Send | Expect |
|---|---|
| any text (e.g. "Oi") | `plain-text`: streamed greeting, markdown rendered |
| click a suggested question | sent as if typed; same as above |
| `/fixture tool-products` | "Buscando no catálogo…" → done; 2 product cards; answer text |
| `/fixture tool-error` | "Consultando seu pedido…" → failed (no code shown); recovery text |
| `/fixture stream-error` | partial text kept + error notice + "Tentar novamente" |
| `/fixture http-500` | error notice; retry resends without duplicating your bubble (in mock mode the resend replays the same fixture, so the error shows again — expected) |
| `/fixture http-429-rate-limited` | notice + input disabled with 30 s countdown, then re-enabled with retry (retry replays the same 429 in mock mode) |
| `/fixture http-429-budget-exhausted` | notice + input disabled, no retry |
| `/fixture http-401` | redirect to `/login?reason=expired&callbackUrl=/` showing "Sua sessão expirou" |
| a message asking for an image, or the hostile string from contracts/ui-rendering.md via a temporary fixture | no image rendered, no network request to the image URL (DevTools → Network) |

Also check: "Parar" during a stream keeps the partial text and shows no error; Shift+Enter adds a
newline; a blank message cannot be sent; a fast double Enter sends once.

Production fail-closed check: `pnpm build && NODE_ENV=production pnpm start` without `CHAT_MODE`
→ `/api/chat` proxies to `BACKEND_URL` (errors if unset) instead of replaying fixtures.

## Mobile check (375 px)

DevTools → device toolbar → 375 × 667. Replay every row above and confirm: no horizontal page
scroll, input pinned at the bottom, product cards in one column, long URLs/tables wrap or scroll
inside the bubble. Attach a 375 px screenshot to the final PR description.
