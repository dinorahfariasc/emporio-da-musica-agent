> **FAKE-MODE PLACEHOLDER — not a real model run.** Reconstructed from the scripted scenario
> `us1-1-violoes-ate-1000` (`backend/evals/scenarios/us1_products.yaml`) and the deterministic fake
> provider. To be replaced by a live export (`uv run python -m evals --live --export
> docs/conversations/`) once #8/#10 are deployed. See `docs/conversations/README.md`.

- Scenario id: `us1-1-violoes-ate-1000`
- Mode: fake (scripted router + fake model)
- Date: placeholder

---

**Customer:** Quais violões vocês têm até R$ 1000?

**Melody** _(tool call: `search_products`, args `{query: "violão", max_price_brl: 1000, category_id: 5}`)_

**Melody:** Temos algumas opções de violões até R$ 1.000, incluindo o Yamaha C40. Posso te
passar os detalhes e a disponibilidade de algum modelo específico?

_Required facts checked by the scenario: the answer must mention "Violões" and "Yamaha C40", and
must not mention products above the price band ("Martin D-28", "Giannini GF-3D")._
