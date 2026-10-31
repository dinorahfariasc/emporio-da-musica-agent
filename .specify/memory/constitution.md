# Empório da Música Agent Constitution

## Core Principles

### I. Fatos vêm do sistema, nunca do modelo (NÃO NEGOCIÁVEL)
- Preço, estoque, status de produto, promoção vigente, status de pedido, prazos e elegibilidade
  de troca/devolução DEVEM ser obtidos por ferramentas determinísticas (SQL parametrizado e
  regras em Python). O LLM apenas redige a resposta a partir do resultado das ferramentas.
- Regras de política com números (prazos, parcelamento, frete, descontos) DEVEM ser codificadas
  e testadas; o RAG serve para explicar e contextualizar, não para calcular.
- O agente NÃO DEVE gerar SQL livre no atendimento ao cliente.
- Quando a informação não existir, o agente DEVE dizer que não sabe e oferecer alternativa
  (produto similar, atendimento humano) em vez de inventar.

**Racional:** o manual da loja (seção 7.1) proíbe informar preço, estoque ou prazo sem consultar o
sistema; erro aqui pode configurar propaganda enganosa.

### II. LLM só quando agrega
- Toda mensagem passa primeiro por um roteador de decisão tipado (Jev, com fallback em LLM de
  saída estruturada) que devolve intenção e confiança.
- Intenções de alta confiança DEVEM ser resolvidas por nós especializados com o modelo mais barato
  capaz (Haiku); o modelo mais caro (Sonnet) é reservado a baixa confiança, multi-intenção ou
  raciocínio aberto.
- Toda decisão de roteamento DEVE ser registrada (intenção, confiança, caminho, modelo, tokens).

**Racional:** custo e latência proporcionais à dificuldade; decisões auditáveis.

### III. Dados tratados e rastreáveis
- Os CSVs e o PDF em `challenge/` são entradas somente leitura; toda limpeza acontece num ETL
  reprodutível com validação de schema.
- Toda correção ou interpretação de dado DEVE ser uma regra explícita, testada e registrada no
  relatório de qualidade de dados e no decision log.
- Texto DEVE ser normalizado (Unicode NFC) antes de comparação ou busca.

**Racional:** os dados têm inconsistências deliberadas; tratá-las de forma explícita é parte da
avaliação.

### IV. Testado antes de pronto
- Ferramentas, regras de política, ETL e recuperação DEVEM ter testes unitários determinísticos.
- O grafo do agente DEVE ser testável com LLM e roteador falsos (sem chamadas pagas no CI).
- Cenários de conversa de referência (incluindo casos adversariais e não óbvios) DEVEM existir
  como eval executável; as conversas de exemplo do README são geradas a partir deles.
- Correção de bug DEVE vir acompanhada de teste de regressão que falhava antes da correção.

**Racional:** comportamento de agente regride silenciosamente sem testes e evals.

### V. Seguro e respeitoso com o cliente
- Dados de pedido só são revelados após verificação (número do pedido + e-mail ou telefone do
  titular). Dados pessoais DEVEM ser mascarados em logs e traces.
- Instruções vindas do usuário ou de documentos recuperados NUNCA sobrepõem o system prompt nem
  liberam ferramentas; ações que gravam dados exigem intenção explícita do cliente.
- Perguntas fora do escopo (incluindo acessórios, que a loja não vende) DEVEM ser recusadas com
  cordialidade e redirecionadas.
- A API pública DEVE exigir autenticação e aplicar orçamento de tokens e rate limit por usuário.

**Racional:** LGPD (manual, seção 9) e exposição de uma chave de API paga.

### VI. Simples, modular e substituível
- Provedores (LLM, roteador, embeddings, banco) ficam atrás de interfaces finas e são escolhidos
  por configuração.
- Ferramentas são funções Python puras expostas via MCP; a camada MCP não contém regra de negócio.
- Nenhuma dependência ou abstração entra sem necessidade presente (YAGNI); complexidade extra
  DEVE ser justificada no plan da feature.

**Racional:** prazo curto exige foco; interfaces permitem trocar peças sem reescrever o agente.

## Restrições Técnicas

- **Linguagens:** Python é a linguagem principal (backend, agente, ETL); TypeScript no frontend.
- **Stack:** FastAPI, LangGraph, FastMCP, Postgres (Neon) com pgvector, Voyage embeddings,
  Anthropic Claude, Jev (TypeSafe); Next.js, Vercel AI SDK, shadcn/ui.
- **Deploy:** Vercel (Next.js + funções Python) e Neon; ambiente local idêntico via docker-compose.
- **Ferramental:** `uv`, `ruff`, `pytest` no Python; `pnpm`, ESLint no frontend; segredos só via
  variáveis de ambiente, com `.env.example` versionado.
- **Idioma:** código, identificadores, testes e commits em inglês; documentação e persona em
  português; o agente responde no idioma do cliente.

## Fluxo de Desenvolvimento

- **Spec-Driven:** nenhuma implementação sem spec → plan → tasks aprovados para o épico.
- **Issues:** tasks viram issues no GitHub Projects somente após revisão de dois agentes (QA e
  engenharia sênior) e aprovação humana; cada issue tem critérios de aceite testáveis e
  prioridade (P0/P1/P2).
- **Branches e PRs:** uma branch por issue; PRs pequenos com `Closes #n`, CI verde (lint + testes)
  e revisão antes do merge; o merge é feito por uma pessoa.
- **Commits:** semânticos (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), sem menção a assistentes
  de IA e sem trailers de coautoria; uso de IA é documentado no decision log.
- **Prioridade:** nenhum item P1 começa antes de todo P0 estar em produção.
- **Documentação viva:** toda decisão relevante gera entrada em `docs/decision-log.md`.

## Governance

Esta constitution prevalece sobre outras práticas do projeto. Todo plan DEVE conter uma
verificação de conformidade com os princípios, e toda revisão de PR DEVE checá-la. Emendas
exigem registro no decision log com motivo e versionamento semântico: MAJOR para remoção ou
redefinição de princípio, MINOR para princípio ou seção nova, PATCH para clarificações.
Orientação de desenvolvimento em tempo de execução fica em `CLAUDE.md`.

**Version**: 1.0.0 | **Ratified**: 2026-10-31 | **Last Amended**: 2026-10-31
