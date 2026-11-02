# Catálogo por preço

**O que demonstra:** Busca no catálogo com filtro de preço calculado em Python (preço promocional quando houver), só produtos vendáveis, e recomendação com uma característica em comum e uma diferença entre as opções. Na segunda pergunta ela mantém o contexto.

- Modo: **live**, agente real (não é placeholder)
- Data: 01/11/2026 (domingo; a loja estava fechada)
- Ambiente: stack local via Docker Compose (`docker compose up`), modelos via OpenRouter
- Roteador: `perplexity/pplx-decider-v1.2`; respostas: `openai/gpt-6-luna` (especialista) e
  `deepseek/deepseek-v4.1-flash` (geral), conforme a intenção classificada
- As linhas `>` mostram a intenção, o modelo e as ferramentas chamadas em cada turno (com os
  argumentos); o texto da Melody está exatamente como foi gerado.

---

**Cliente:** Quais opções de violões disponíveis custando até R$1000?

> intent `product_search`, model `openai/gpt-6-luna`; tools: `search_products({"query": "violão", "max_price_brl": 1000, "only_sellable": true, "limit": 5})`

**Melody:** Olá! Encontrei estas opções de violões disponíveis por até R$ 1.000:

- **Tagima Memphis AC-39 Nylon Natural — R$ 429,90**: cordas de nylon, como os demais clássicos; é a opção mais econômica e tem corpo leve.
- **Yamaha C40 Nylon Natural — R$ 599,90**: também clássico de nylon; tem tampo em Spruce, diferente do tampo em Linden do Tagima.
- **Giannini GN-15 Nylon Cedr Natural — R$ 689,00**: clássico de nylon com tampo em cedro, que oferece sonoridade quente e encorpada; custa mais que o C40.
- **Yamaha F310 Aço Natural — R$ 699,90**: violão folk, diferente das opções de nylon por usar cordas de aço e ter timbre encorpado.
- **Yamaha C70 Nylon Natural — R$ 849,00**: clássico de nylon como o C40, mas tem tampo em Spruce sólido e é descrito como modelo intermediário.

Todos constam em estoque. Você prefere cordas de nylon ou de aço? Posso ajudar a escolher.

**Cliente:** Qual desses é melhor pra quem está começando?

> intent `product_search`, model `openai/gpt-6-luna`; tools: `search_products({"query": "violão iniciante nylon Yamaha C40 Tagima Memphis AC-39", "max_price_brl": 1000, "only_sellable": true, "limit": 5})`

**Melody:** Para começar, eu escolheria o **Tagima Memphis AC-39 Nylon**, por **R$ 429,90**. É um violão clássico de nylon, como o Yamaha C40, e a descrição destaca que é indicado para iniciantes, com corpo leve e confortável para estudar. Também custa menos que o C40 (R$ 599,90) e o C70 (R$ 849,00).

Ele consta disponível em estoque. Se preferir um violão de aço, o Yamaha F310 é uma opção diferente, com timbre mais encorpado. Quer que eu compare os dois tipos de corda?
