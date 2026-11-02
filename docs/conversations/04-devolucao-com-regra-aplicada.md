# Devolução por arrependimento e defeito (caso não trivial)

**O que demonstra:** Aplica as políticas a um pedido real: verifica o pedido com e-mail (`get_order_status`), pergunta o canal da compra e decide com `check_return_eligibility`, que calcula os prazos em Python (7 dias do recebimento para arrependimento em compra online, §4.1; 30 dias e garantia legal de 90 dias para defeito, §4.2/§8.1). Ambos vencidos; oferece o caminho alternativo (garantia do fabricante com intermediação da loja).

- Modo: **live**, agente real (não é placeholder)
- Data: 01/11/2026 (domingo; a loja estava fechada)
- Ambiente: stack local via Docker Compose (`docker compose up`), modelos via OpenRouter
- Roteador: `perplexity/pplx-decider-v1.2`; respostas: `openai/gpt-6-luna` (especialista) e
  `deepseek/deepseek-v4.1-flash` (geral), conforme a intenção classificada
- As linhas `>` mostram a intenção, o modelo e as ferramentas chamadas em cada turno (com os
  argumentos); o texto da Melody está exatamente como foi gerado.

---

**Cliente:** Me arrependi da minha compra, posso devolver meu pedido?

> intent `service_request`, model `openai/gpt-6-luna`

**Melody:** Olá! Posso verificar, sim. Para consultar a devolução, me informe o número do pedido e o e-mail ou telefone cadastrado. A compra foi feita online?

**Cliente:** É o pedido 7, meu email é leticia.rocha@jmail.com

> intent `order_status`, model `deepseek/deepseek-v4.1-flash`; tools: `get_order_status({"order_id": 7, "contact": "leticia.rocha@jmail.com"})`

**Melody:** Encontrei seu pedido 7: Shelby SU-21S Soprano Sunburst, entregue em 17/02/2026.

Para a devolução por arrependimento, só é possível para compras feitas online. A sua compra foi feita pela internet?

**Cliente:** Comprei pelo site. E se o problema for defeito?

> intent `policy_question`, model `deepseek/deepseek-v4.1-flash`; tools: `check_return_eligibility({"order_id": 7, "reason": "regret", "bought_online": true})`, `check_return_eligibility({"order_id": 7, "reason": "defect"})`

**Melody:** Verifiquei as duas situações para o pedido 7:

**Arrependimento (compra online):** ❌ o prazo de 7 dias já terminou. A entrega foi em 17/02/2026 e o prazo ia até 24/02/2026 — hoje é 01/11/2026, então não é mais possível devolver por arrependimento.

**Defeito:** a garantia legal também já expirou. Nesse caso, a orientação é acionar a **garantia do fabricante** — e, se você quiser, a loja pode intermediar esse processo mediante solicitação. 

Quer que eu registre o pedido de intermediação com o fabricante ou prefere falar com um atendente humano para tratar disso?
