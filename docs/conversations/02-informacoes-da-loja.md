> **FAKE-MODE PLACEHOLDER — not a real model run.** Reconstructed from the scripted scenario
> `us2-1-endereco` (`backend/evals/scenarios/us2_policies.yaml`) and the deterministic fake
> provider. To be replaced by a live export (`uv run python -m evals --live --export
> docs/conversations/`) once #8/#10 are deployed. See `docs/conversations/README.md`.

- Scenario id: `us2-1-endereco`
- Mode: fake (scripted router + fake model)
- Date: placeholder

---

**Customer:** Qual o endereço e o telefone da loja?

**Melody** _(tool call: `get_store_info`, args `{}`)_

**Melody:** Estamos na Rua 14 de Maio, 3200, em Campo Grande/MS. Você pode nos ligar ou chamar no
WhatsApp pelo (67) 3341-4444, ou escrever para contato@emporiodamusica.com.br.

_Required facts checked by the scenario: the address, the phone number and the e-mail must appear
exactly as above; an outdated phone number found in the manual (3321-4500) and a misspelled store
name ("empório") must not appear._
