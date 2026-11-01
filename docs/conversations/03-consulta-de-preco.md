> **FAKE-MODE PLACEHOLDER — not a real model run.** Reconstructed from the scripted scenario
> `us1-2-gd20-sem-promocao` (`backend/evals/scenarios/us1_products.yaml`) and the deterministic
> fake provider. To be replaced by a live export (`uv run python -m evals --live --export
> docs/conversations/`) once #8/#10 are deployed. See `docs/conversations/README.md`.

- Scenario id: `us1-2-gd20-sem-promocao`
- Mode: fake (scripted router + fake model)
- Date: placeholder

---

**Customer:** Quanto custa o Takamine GD20?

**Melody** _(tool calls: `get_product` args `{name: "Takamine GD20"}`, then
`calculate_payment_options` args `{product_id: 95}`)_

**Melody:** O Takamine GD20 custa R$ 2.199,00, sem promoção ativa no momento. Posso te mostrar as
opções de parcelamento, se quiser.

_Required facts checked by the scenario: the price (2199.00) and the parcelamento base (2089.05 for
a cash/à vista option, per the payment rules in `app/catalog/rules.py`); the answer must not invent
a 12% discount that doesn't apply to this product._
