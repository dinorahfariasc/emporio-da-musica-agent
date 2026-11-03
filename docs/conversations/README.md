# Example conversations

Requirement: 3–5 conversations in `.md`/`.txt`/image, covering varied scenarios, at least
one non-trivial (real-time data lookup or a policy rule applied).

All five are **live runs** of the real agent (not hand-written, not fake-mode), recorded on
2026-11-01 against the local Docker stack with the production models (OpenRouter). Each file
shows, per turn, the classified intent, the model that answered and every tool call with its
arguments, then Melody's text exactly as generated.

| File | Scenario (brief suggestion) | Why it matters |
|---|---|---|
| [`01-catalogo-por-preco.md`](01-catalogo-por-preco.md) | "Quais opções de violões disponíveis custando até R$1000?" | Catalog search with a price filter applied in Python, sellable products only, recommendation with a shared trait and a difference, follow-up keeps context |
| [`02-informacoes-da-loja.md`](02-informacoes-da-loja.md) | "Qual o endereço da loja?" | Store info from the store clock (knows it is closed today and when it reopens) plus the manual for Sundays |
| [`03-consulta-de-preco.md`](03-consulta-de-preco.md) | "Quanto custa o Takamine GD20?" | Price, 12x instalments and the 5% PIX discount computed by a tool; exact stock for 3 units |
| [`04-devolucao-com-regra-aplicada.md`](04-devolucao-com-regra-aplicada.md) | "Me arrependi da minha compra, posso devolver meu pedido?" | **Non-trivial:** verifies a real order, asks the purchase channel, applies the return and warranty rules (§4.1, §4.2, §8.1) with deterministic date math, offers the alternative path |
| [`05-fora-do-escopo-e-seguranca.md`](05-fora-do-escopo-e-seguranca.md) | Out of scope (brief requirement) | Off-topic question, an accessory the store does not sell, prompt extraction and a fake "manager-approved" discount |

## How they were produced

Each conversation was sent turn by turn to `POST /api/chat` through the frontend (logged in as
a CLI-created account), with the full history on every turn, exactly as the chat UI does.
To reproduce, run the stack (`README.md` → Run locally), log in at http://localhost:3000 and type
the same messages. Answers vary slightly between runs (temperature, model updates); the facts
(prices, stock, dates, eligibility) come from tools and do not.

The scripted scenarios in `backend/evals/scenarios/` cover the same behaviours (and more) with
assertions on tool calls and facts: `uv run python -m evals --live` in `backend/`.
