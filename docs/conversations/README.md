# Example conversations

Brief requirement: 3–5 conversations in `.md`/`.txt`/image, covering varied scenarios, at least
one non-trivial (real-time data lookup or a policy rule applied).

## Selection criteria

1. The 4 scenarios suggested in the brief, each mapped to an existing eval scenario so the
   transcript is reproducible, not hand-written:
   - Catalog by price — `us1-1-violoes-ate-1000` ("Quais violões vocês têm até R$ 1000?")
   - Store info — `us2-1-endereco` ("Qual o endereço e o telefone da loja?")
   - Price lookup — `us1-2-gd20-sem-promocao` ("Quanto custa o Takamine GD20?")
   - Return policy (non-trivial: policy rule applied to a real order + date) —
     `us6-1-arrependimento-elegivel` ("Quero devolver o pedido 4...")
2. One adversarial or English/multilingual conversation, to show safety and language handling —
   `us5-3-extracao-de-prompt` (prompt-extraction attempt) or `us5-8-troca-de-idioma`
   (language switch mid-conversation). Both are `live_only` scenarios (see below).

## Status: placeholders, not final

`backend/evals/__main__.py` does not yet have an `--export` flag. The final conversations must be
produced with:

```bash
cd backend
uv run python -m evals --live --export docs/conversations/
```

against the deployed agent, after #8 (MCP) and #10 (auth/limits/deploy) land and the models in
DL-012 are confirmed in production. That export is **not implemented yet** — see
`docs/delivery-checklist.md` §4 — and is out of scope for this docs track.

Until then, `docs/conversations/*.md` (other than this file) are **fake-mode placeholders**:
reconstructed by hand from the scripted scenario YAML (`backend/evals/scenarios/`) and the fake
provider's deterministic replies, not an actual model run. Each placeholder file says so at the
top and names its source scenario id. The two `live_only` adversarial/language scenarios have no
fake-mode run at all (the fake router/model only replay a script, so they can't demonstrate real
safety behaviour); their file is a stub describing what the live export should contain.

## File naming

`NN-short-slug.md`, numbered in the order above. Each file: scenario id, mode (`live` or
`fake-mode placeholder`), model(s) used, date, then the turn-by-turn transcript (user / Melody /
tool calls with arguments and results, when shown).
