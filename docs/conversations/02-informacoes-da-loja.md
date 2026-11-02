# Informações gerais da loja

**O que demonstra:** Endereço e horário vindos de `get_store_info` (relógio da loja: sabe que hoje está fechada e quando reabre) e do manual (`search_policies`) para o domingo.

- Modo: **live**, agente real (não é placeholder)
- Data: 01/11/2026 (domingo; a loja estava fechada)
- Ambiente: stack local via Docker Compose (`docker compose up`), modelos via OpenRouter
- Roteador: `perplexity/pplx-decider-v1.2`; respostas: `openai/gpt-6-luna` (especialista) e
  `deepseek/deepseek-v4.1-flash` (geral), conforme a intenção classificada
- As linhas `>` mostram a intenção, o modelo e as ferramentas chamadas em cada turno (com os
  argumentos); o texto da Melody está exatamente como foi gerado.

---

**Cliente:** Qual o endereço da loja?

> intent `store_info`, model `openai/gpt-6-luna`; tools: `get_store_info({})`, `search_policies({"query": "horário de funcionamento da loja aos domingos, sábados e feriados", "limit": 3})`

**Melody:** Olá! A loja fica na **Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, 79202-333**. Hoje está fechada e abre **terça-feira, 3 de novembro, às 9h**. Quer também o telefone ou WhatsApp?

**Cliente:** Vocês abrem domingo?

> intent `store_info`, model `openai/gpt-6-luna`; tools: `get_store_info({})`, `search_policies({"query": "horário de funcionamento aos domingos", "limit": 3})`

**Melody:** Não, aos domingos a loja fica fechada. O horário normal é de segunda a sexta, das 9h às 18h, e aos sábados, das 9h às 13h. A próxima abertura é terça-feira, às 9h. Quer mais alguma informação?
