# Consulta de preço, pagamento e estoque

**O que demonstra:** Preço do Takamine GD20, parcelamento em 12x e desconto de 5% no PIX calculados por `calculate_payment_options` (o modelo não faz contas), e estoque exato para 3 unidades com `get_product(quantity=3)`.

- Modo: **live**, agente real (não é placeholder)
- Data: 01/11/2026 (domingo; a loja estava fechada)
- Ambiente: stack local via Docker Compose (`docker compose up`), modelos via OpenRouter
- Roteador: `perplexity/pplx-decider-v1.2`; respostas: `openai/gpt-6-luna` (especialista) e
  `deepseek/deepseek-v4.1-flash` (geral), conforme a intenção classificada
- As linhas `>` mostram a intenção, o modelo e as ferramentas chamadas em cada turno (com os
  argumentos); o texto da Melody está exatamente como foi gerado.

---

**Cliente:** Quanto custa o Takamine GD20?

> intent `product_details`, model `openai/gpt-6-luna`; tools: `get_product({"name": "Takamine GD20"})`

**Melody:** Olá! O Takamine GD20 Dreadnought Natural custa **R$ 2.199,00** e temos **5 unidades em estoque**. Ele tem tampo sólido em cedro, corpo em sapele e timbre quente e definido. Precisa de mais alguma informação?

**Cliente:** Dá pra parcelar em 12x sem juros? E no PIX tem desconto?

> intent `payment_options`, model `openai/gpt-6-luna`; tools: `get_product({"name": "Takamine GD20"})`, `search_policies({"query": "formas de pagamento parcelamento em 12 vezes sem juros e desconto no PIX; promoções e acumulação de descontos", "limit": 5})`, `calculate_payment_options({"product_id": 95})`

**Melody:** Sim! O Takamine GD20 pode ser parcelado em **12x de R$ 183,25 sem juros**, ou você pode pagar no PIX por **R$ 2.089,05**, com 5% de desconto sobre o preço de R$ 2.199,00. O desconto do PIX não se acumula com preços promocionais. Precisa de mais alguma informação?

**Cliente:** Tem 3 unidades? Quero comprar pra minha banda.

> intent `product_details`, model `openai/gpt-6-luna`; tools: `get_product({"name": "Takamine GD20", "quantity": 3})`

**Melody:** Sim, temos **5 unidades** do Takamine GD20 em estoque, então há disponibilidade para as 3 que você precisa. Você pode comprar pelo site, na loja ou pelo WhatsApp. Posso ajudar com mais alguma informação?
