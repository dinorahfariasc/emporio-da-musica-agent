> **FAKE-MODE PLACEHOLDER — not a real model run.** Reconstructed from the scripted scenario
> `us6-1-arrependimento-elegivel` (`backend/evals/scenarios/us6_actions.yaml`), which pins the
> clock (`now: 2025-12-25T10:00`) because at the real delivery date every dataset order is outside
> every return window (see DL-013). To be replaced by a live export (`uv run python -m evals
> --live --export docs/conversations/`) once #8/#10 are deployed — the live version will show a
> model correctly refusing this same request at today's date and offering the defect path instead
> (see DL-013, "A live model asked to open a return for order 4 correctly refused"). See
> `docs/conversations/README.md`.

- Scenario id: `us6-1-arrependimento-elegivel`
- Mode: fake (scripted router + fake model, scripted clock)
- Date: placeholder (scripted "now" = 2025-12-25)

---

**Non-trivial scenario:** applies the store's return policy (manual §4.1 — 7-day regret window
for online purchases) to a real order, computed from its delivery date, not asserted by the model.

**Customer:** Quero devolver o pedido 4, comprei online e não gostei. Meu telefone é
67998123456.

**Melody** _(tool calls: `get_order_status` args `{order_id: 4, contact: "67998123456"}`, then
`check_return_eligibility` args `{order_id: 4, reason: "regret", bought_online: true}`)_

**Melody:** Verifiquei seu pedido 4. Como você comprou online, tem até 7 dias corridos após a
entrega para se arrepender (manual §4.1) — e seu prazo ainda não venceu (até 2025-12-29). Posso
abrir a devolução agora?

**Customer:** Sim, pode abrir a devolução.

**Melody** _(tool call: `request_return`, args `{order_id: 4, reason: "regret", details: "não
gostei", confirmed_by_customer: true, bought_online: true}`)_

**Melody:** Pronto! Abri a solicitação de devolução do pedido 4. Você vai receber as instruções
por e-mail.

_Required facts checked by the scenario: the eligibility tool must return `eligible: true`, rule
`4.1`, deadline `2025-12-29`; the write only happens after the explicit customer confirmation, and
the action tool returns a `type: "return"` with a `request_id` (never invented by the model)._
