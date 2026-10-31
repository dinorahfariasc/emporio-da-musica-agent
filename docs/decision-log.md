# Decision Log

Registro vivo de como as decisões deste projeto foram tomadas, quais alternativas foram
consideradas e como assistentes de IA participaram do processo. Atualizado ao longo do
desenvolvimento; o README resume e aponta para cá.

**Formato de cada entrada:** contexto → decisão → alternativas → justificativa → papel da IA.

---

## DL-001 — Kickoff: leitura do desafio e dos dados (2026-10-31)

**Contexto.** Desafio técnico Artefact (AI Engineer): agente de atendimento para a loja
fictícia Empório da Música, com CSVs operacionais e um manual de políticas em PDF.
Prazo: P0 pronto em 2026-11-01 à noite; 2026-11-02 reservado a melhorias.

**O que foi feito.** Leitura completa do enunciado, do manual (8 páginas) e perfilamento
dos 6 CSVs. Foram identificadas inconsistências que viram requisitos de tratamento de dados:

| Fonte | Achado |
|---|---|
| products | IDs 135–144: nome contradiz descrição (ex.: "Music Man Bass 1X" descrito como Fender Jazz Bass); specs contradizem descrição (5 vs 4 cordas, 88 vs 61 teclas); `specs` com esquemas diferentes por categoria |
| products | 96 `active` com estoque 0; 113 `discontinued`; 136 `discontinued` com 13 unidades; 130 `coming_soon` mas presente em pedidos |
| promotions | Duplicatas por produto (96: 18% e 40%); apenas 4 ativas (90, 94, 121, 127); sem datas de vigência |
| orders | Totais divergentes da soma dos itens (pedido 3: 3498 vs 3450; pedido 20: 1488 vs 1400) |
| customers | "Ponta Porã" com duas codificações Unicode diferentes |
| manual | Dois WhatsApps (3341-4444 na seção 1.2, 3321-4500 na seção 7); e-mail com e sem acento; tabela de parcelamento contradiz a seção 3.1; arrependimento de 7 dias vale só para compras online e os pedidos não informam o canal |

Também foram renomeados os arquivos do desafio para caminhos sem espaços/acentos
(`challenge/`, `challenge/data/*.csv`, `store_policies.pdf`).

**Papel da IA.** Claude Code leu PDFs e CSVs e produziu o perfilamento; eu validei os achados.

---

## DL-002 — Arquitetura e workflow definidos em sessão de "grilling" (2026-10-31)

**Contexto.** Antes de especificar, usei uma skill de *grilling* (entrevista estruturada em
rodadas, cada pergunta com uma recomendação) para fechar a árvore de decisões. Também usei a
descrição da vaga como baseline do que é esperado (LangGraph, Vercel AI SDK, MCP, assistentes
que executam tarefas, IA em produção).

### Decisões

| Tema | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| Orquestração | **LangGraph** | SDK puro, PydanticAI, LangChain agents | O fluxo é naturalmente um grafo: roteador → nós especializados → fallback (aresta condicional). Citado na vaga. |
| Roteamento | **Jev (TypeSafe AI)** como classificador de intenção, com **Claude Haiku (saída estruturada) como fallback** | Só LLM roteando | Decisão tipada com confiança, em milissegundos e custo ~zero; LLM só entra para redigir ou para casos ambíguos. Comparação Jev × Haiku vira material do README. |
| LLMs | **Claude Haiku 4.5** redige respostas de nós especializados; **Claude Sonnet 5.5** num agente ReAct para baixa confiança / multi-intenção | Um único modelo para tudo | Custo e latência proporcionais à dificuldade. |
| Dados | Ferramentas **determinísticas** com SQL parametrizado; preço/estoque/desconto calculados em Python | Agente text-to-SQL | O manual proíbe informar preço/estoque sem consultar o sistema; text-to-SQL é não determinístico. |
| Políticas | **RAG híbrido** (full-text Postgres + pgvector), chunks por seção do manual | Manual inteiro no prompt; só BM25 | Manual é pequeno, mas a arquitetura precisa escalar; busca semântica funciona entre idiomas. |
| Embeddings | **Voyage AI** (free tier) | fastembed local, Gemini, sem vetores | Anthropic não tem embeddings; modelo local não cabe em função serverless. |
| Recomendação | `find_similar_products`: filtros estruturados + similaridade vetorial | Só busca por nome | "Não temos a guitarra X, mas temos similares" — atende seção 7.3 do manual (sugerir alternativas). |
| Ferramentas | Expostas via **servidor MCP** (FastMCP) montado no FastAPI | Funções chamadas direto | Citado na vaga; mesmo servidor pode ser usado por Claude Desktop/Code. |
| Ações | `request_return`, `register_complaint`, `handoff_to_human`; confirmação via `interrupt` (P1) | Agente só responde | Vaga pede assistentes que executam tarefas. |
| Identidade | Pedido só é revelado com nº do pedido + e-mail ou telefone | Confiar no usuário logado | LGPD; o usuário logado é o avaliador, não o cliente. |
| Persona | **Melody**, tom informal-profissional (manual 7.1), fluxo da seção 7.2, multilíngue | — | Visual/branding virão de um mockup Figma depois. |
| Datas | Usar a **data real** | Data de referência configurável | Simplicidade; consequência aceita: devoluções da base serão recusadas por prazo. |
| Frontend | **Next.js + Vercel AI SDK (`useChat`) + shadcn/ui**, i18n PT/EN | CLI, Streamlit | Entrega em estado de uso real; AI SDK citado na vaga. |
| Deploy | **Tudo na Vercel** (Next.js + funções Python) + **Neon Postgres** (free) | Railway, HF Spaces, Fly | Grátis, um só deploy e um só banco; volume de acesso baixo. |
| Acesso | Login sem cadastro público (contas criadas por script) + orçamento diário de tokens e rate limit | Público aberto | Chave paga exposta. |
| Qualidade | pytest (LLM/Jev falsos), evals de conversas de referência, CI no GitHub Actions; guardrails P0; Langfuse P1 | — | "O que funciona em produção". |
| Dados (ETL) | Módulo `etl/` com validação Pydantic, regras de correção explícitas e relatório gerado | Limpeza ad hoc | Reprodutível e testável. |

### Regras de correção de dados
- Total de pedido divergente: manter `total_brl` original (valor pago) e sinalizar.
- Nome × descrição: o **nome** prevalece; descrição contraditória não é exibida.
- Specs × descrição: **specs** prevalecem.
- Promoções: só `is_active=1`; se houver mais de uma ativa, vale a maior.
- `discontinued` não está à venda; estoque 0 = indisponível (sugerir alternativas); `coming_soon` = "em breve".
- Contato oficial: seção 1.2 (67) 3341-4444; e-mail sem acento; conflito documentado.
- Parcelamento: seção 3.1 prevalece sobre a tabela.
- Texto normalizado em Unicode NFC.

### Prioridades
- **P0 (até 01/11 à noite):** agente completo, backend + MCP, chat Next.js com login, deploy, README, decision log, 3–5 conversas.
- **P1:** limite de tokens refinado, histórico persistido, i18n, `interrupt`, Langfuse, Playwright, demo MCP no Claude Desktop.
- **P2 (02/11):** dashboard admin (gráficos + chat de insights), notebook de EDA, LLM-as-judge.

### Processo
- **Spec-Driven Development com Spec Kit**: constitution → uma spec por épico
  (`001-data-foundation`, `002-agent-core`, `003-chat-web`, `004-auth-limits-deploy`,
  `005-admin-dashboard`) → plan → tasks.
- **Ágil no GitHub**: tasks viram rascunhos de issues, revisados por dois agentes (QA e
  engenharia sênior) antes de serem criados no GitHub Projects; PRs com `Closes #n`.
- **Paralelização**: backend e frontend em worktrees separadas (Orca) após as specs.
- Conversas de exemplo **geradas** por script contra o agente real (também servem de eval),
  incluindo cenários não óbvios (prompt injection, pedido de terceiros, PIX + promoção,
  produto descontinuado com estoque, troca de idioma).

**Papel da IA.** Claude Code conduziu o grilling (perguntas + recomendações); as decisões
foram minhas. Pesquisa sobre o Jev feita via busca web pelo agente.
