# Empório da Música — product overview for UI/UX (Figma brief)

Source of truth for behaviour: `specs/002-agent-core`, `003-chat-web`, `004-auth-limits-deploy`,
`docs/contracts/chat-stream.md`. This brief collects what the interface must show. Copy is
pt-BR first, with an EN switch (#13, done). The UI formats values; it never computes prices,
discounts, stock or eligibility.

## 1. What it is
A website whose single product is a chat with **Melody**, the virtual assistant of a music store
(instruments, accessories, audio). Customers ask about products, prices, promotions, payment
methods, store policies, orders, returns and complaints. The reviewer plays the customer.

## 2. Screens
| # | Screen | Route | Purpose |
|---|---|---|---|
| 1 | Login | `/login` | Username + password. No sign-up (accounts are created by the owner). Generic error on failure; temporary lockout message after repeated failures; "session expired" notice when redirected (`?reason=expired`). |
| 2 | Chat (empty) | `/` | Melody greeting + 3–4 suggested questions. |
| 3 | Chat (conversation) | `/` | Messages, streaming answer, tool status, product cards, input. |
| 4 | Chat (error / limit states) | `/` | See section 5. |
| 5 | Header (all screens) | | Store name / Melody identity, PT/EN switch, sign out. |

Later (P2, only if time allows): admin dashboard with insights chat (spec 005, not yet written).

## 3. Chat anatomy
- **Header:** logo/name, language toggle (PT | EN), sign out.
- **Message list:** user bubbles (right) and Melody bubbles (left), markdown rendered
  (paragraphs, lists, bold, links; images blocked). Auto-scroll unless the user scrolled up.
- **Typing indicator:** "Melody está digitando…" until the first content arrives.
- **Tool status line** (inside the assistant turn, one per tool call), states running / done /
  failed, with friendly labels, e.g. "Buscando no catálogo…", "Verificando promoções…",
  "Verificando se dá para trocar ou devolver…". Fallback label "Consultando…". Never show tool
  names or raw errors.
- **Product card** (from `data-products`): name, current price, original price struck through
  and discount % when there is a promotion, availability badge (in stock / out of stock / coming
  soon / discontinued; hidden when unknown). **No image** exists in the data: design a card that
  works without one (category icon or colour block is fine). Cards stack in 1 column on mobile
  and may form a grid on desktop.
- **Input area:** multiline field (Enter sends, Shift+Enter newline), send button, **Stop**
  button while streaming; pinned to the bottom; empty message cannot be sent.
- **Suggested questions:** chips in the empty state.

## 4. What Melody can answer (drives suggestions and example content)
1. Products, prices, availability, promotions, installments and PIX price
   ("Quais violões até R$ 1000?", "Quanto custa o Takamine GD20?").
2. Store policies and info: hours, shipping, warranty, returns (from the policies PDF).
3. Order status with identity check (email + order number; locked after repeated failures).
4. Recommendations when a product is unavailable.
5. Returns, complaints and handoff to a human (writes only on explicit customer request).
6. Stays in scope and in character: refuses off-topic, prompt injection, discount negotiation
   and data of other customers.

Suggested chips (pt-BR): "Quais violões vocês têm até R$ 1.000?", "Qual o horário de
funcionamento?", "Posso parcelar em 12x?", "Como faço para devolver um produto?".

## 5. States to design (each with pt-BR and EN copy)
| State | Behaviour |
|---|---|
| Empty | Greeting + chips. |
| Streaming | Growing bubble, Stop button, input blocked. |
| Stopped by user | Partial answer stays; no error. |
| Rate limited (429) | Inline message, input disabled with visible countdown (default 60 s), then "Tentar novamente". |
| Daily budget exhausted (429) | Inline message, input locked until reset at 00:00 (America/Campo_Grande); no retry button. |
| Server / network error (500) | Inline message + "Tentar novamente"; no duplicate user bubble. |
| Dropped or failed stream | Partial text kept, error text under it, "Tentar novamente". |
| Session expired (401) | Redirect to login with "Sua sessão expirou". |
| Login error / locked | Generic "invalid credentials"; separate "try again later" lockout copy. |
| Handoff to human | Melody states what was recorded and the next step (protocol shown in the text). |

## 6. Non-functional design constraints
- Works at **375 px** with no horizontal scroll; tap targets ≥ 44 px; safe-area insets on iOS.
- Long URLs and tables scroll or wrap inside the bubble.
- Accessible: status announcements (`role="status"`), visible focus, contrast AA, light and
  dark if the brand allows.
- Currency format `R$ 1.234,56`; no status codes or JSON ever shown.

## 7. What I need back from Figma
Colour tokens, type scale, logo, spacing, bubble, product card, status line, input, buttons,
error banners, login screen, mobile and desktop frames. A link to the file (share view) so the
frontend can apply it (#18).
