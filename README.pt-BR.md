# Empório da Música — Melody, a agente de atendimento ao cliente

**🇬🇧 [Click here for the English version](README.md)**

Agente de atendimento ao cliente com IA para a Empório da Música, uma loja fictícia de instrumentos
musicais em Campo Grande/MS (desafio técnico de AI Engineer da Artefact, `challenge/challenge_brief.pdf`).
A agente ("Melody") atende clientes em português ou inglês sobre catálogo, preços, status de pedidos,
políticas da loja e solicitações de devolução/reclamação, com base nos dados reais da loja e no
manual de políticas.

- **Produção:** https://emporio-da-musica-agent.vercel.app (fora do ar no momento, veja
  [Executar em produção](#executar-em-produção); enquanto isso, rode localmente com Docker)
- **Backlog / escopo:** [`docs/planning/backlog.md`](docs/planning/backlog.md)
- **Decisões e uso de IA, na íntegra:** [`docs/decision-log.md`](docs/decision-log.md)
- **Conversas de exemplo:** [`docs/conversations/`](docs/conversations/)
- **Premissas e anomalias dos dados:** [`docs/data-quality-report.md`](docs/data-quality-report.md)

## Sumário

- [Arquitetura](#arquitetura)
- [Executar localmente](#executar-localmente)
- [Executar em produção](#executar-em-produção)
- [Acesso para avaliadores](#acesso-para-avaliadores)
- [Dados](#dados)
- [Decisões principais e trade-offs](#decisões-principais-e-trade-offs)
- [Premissas](#premissas)
- [Fluxo de trabalho com assistente de IA](#fluxo-de-trabalho-com-assistente-de-ia)
- [Servidor MCP](#servidor-mcp)
- [Limitações e próximos passos](#limitações-e-próximos-passos)

## Arquitetura

```mermaid
flowchart LR
    user([Cliente]) --> web["Frontend Next.js<br/>UI de chat, login (Auth.js),<br/>/api/chat como BFF"]
    web -->|"stream SSE<br/>JWT de serviço"| api["Backend FastAPI<br/>/api/chat"]
    api --> agent["Agente<br/>roteador + create_agent<br/>(LangChain/LangGraph)"]
    agent --> tools["Ferramentas<br/>Python puro,<br/>fatos calculados aqui"]
    tools --> db[("Postgres + pgvector<br/>tabelas da loja, índice de busca,<br/>limites, estado da conversa")]
    agent -.->|modelos de chat + roteador| or["OpenRouter"]
    tools -.->|embeddings das consultas| gem["Embeddings Gemini"]
    ext([Cliente MCP externo]) -->|"chave bearer<br/>ferramentas somente leitura"| mcp["/mcp"]
    mcp --> tools
```

Um turno de chat, de ponta a ponta:

```mermaid
sequenceDiagram
    actor C as Cliente
    participant W as Next.js /api/chat
    participant B as FastAPI /api/chat
    participant R as Roteador (decider)
    participant A as Agente (create_agent)
    participant T as Ferramentas
    participant D as Postgres
    C->>W: mensagem (+ histórico recente)
    W->>W: verifica a sessão, assina JWT de curta duração
    W->>B: POST com JWT
    B->>D: limite de requisições e orçamento diário de tokens
    B->>R: classifica a intenção
    R-->>B: intenção + confiança
    B->>A: executa com as ferramentas daquela intenção
    loop enquanto o modelo precisar de fatos
        A->>T: chamada de ferramenta
        T->>D: SQL parametrizado / busca híbrida
        D-->>T: linhas
        T-->>A: resultado em JSON
    end
    A-->>B: eventos de token e de ferramenta
    B-->>W: SSE (AI SDK UI message stream)
    W-->>C: resposta em streaming + cards de produto
    B->>D: registra o uso de tokens
```

Mais diagramas (fluxo de decisão, dados e recuperação, recomendação semântica) em [`docs/architecture.md`](docs/architecture.md).

- **O roteamento acontece em Python puro, não em um nó do LangGraph.** A requisição é classificada
  por intenção primeiro (modelo decider, com fallback para um modelo de chat) e depois exatamente
  uma execução de `create_agent` transmite a resposta com as ferramentas daquela intenção. Veja a
  DL-011 para entender por que um grafo externo foi descartado.
- **Fato ou política?** Fatos vêm de ferramentas determinísticas, políticas vêm de RAG mais regras em Python:

```mermaid
flowchart TD
    q[Mensagem do cliente] --> i{Intenção}
    i -->|preço, estoque, promoção| t1["Ferramentas determinísticas<br/>get_product, calculate_payment_options,<br/>get_active_promotions"]
    i -->|devoluções, horários, regras de pagamento| t2["search_policies<br/>(RAG sobre o manual)<br/>+ regras em Python para prazos"]
    i -->|status do pedido| v{"Número do pedido +<br/>e-mail ou telefone do titular?"}
    v -->|sim| t3[get_order_status]
    v -->|não, ou divergente| deny["Recusa genérica,<br/>bloqueio após falhas repetidas"]
    i -->|devolução, reclamação, humano| act["check_return_eligibility,<br/>depois ferramentas de ação só com<br/>pedido explícito do cliente"]
    i -->|fora do escopo| out["Recusa educada,<br/>oferece instrumentos"]
    t1 --> w[O LLM escreve a resposta só a partir dos resultados das ferramentas]
    t2 --> w
    t3 --> w
    act --> w
```

- **Fatos nunca são calculados pelo LLM.** Preço, estoque, elegibilidade a desconto e prazos de
  devolução são Python puro (`app/catalog/rules.py`, `app/policies/returns.py`); as ferramentas
  devolvem JSON que o modelo só pode ler e citar, nunca derivar (princípio I da constituição).
- **A recuperação é híbrida**: busca textual do Postgres (`pt_unaccent`) e similaridade de cosseno
  do pgvector, combinadas por Reciprocal Rank Fusion, sobre trechos de políticas e documentos por
  produto (DL-010).
- **Um projeto Vercel, dois Services** (`vercel.json`): o `frontend` Next.js é público; o `backend`
  FastAPI é privado, acessado apenas pelo service binding `BACKEND_URL`.

Veja [`specs/002-agent-core/`](specs/002-agent-core/) para o design completo (modelo de dados,
contratos, tarefas) e [`specs/001-data-foundation/`](specs/001-data-foundation/) para o ETL e o
índice de recuperação.

## Executar localmente

### Com Docker (recomendado)

Requisitos: Docker. Um comando sobe o Postgres (pgvector), o backend FastAPI e o frontend Next.js;
mais detalhes e solução de problemas em [`DOCKER.md`](DOCKER.md).

```bash
cp backend/.env.example backend/.env   # then set a real LLM provider and key (below)
docker compose up --build
```

- Frontend: http://localhost:3000 (página de login)
- Backend: http://localhost:8000/api/health
- Postgres: `localhost:5433`, usuário/senha/banco `emporio`

O chat precisa de um modelo real: em `backend/.env` defina `LLM_PROVIDER=openrouter`,
`ROUTER_PROVIDER=openrouter` e `OPENROUTER_API_KEY` (veja [Variáveis de ambiente](#variáveis-de-ambiente)).
`LLM_PROVIDER=fake` é um modelo roteirizado apenas para testes automatizados: no chat, toda
mensagem falha. O arquivo compose já define a URL do banco, a URL do backend e segredos apenas de
desenvolvimento, então nada mais é necessário localmente.

**Carregue os dados** (primeira execução, banco vazio) e **crie um login** (não há página de
cadastro, por design; as contas vêm de uma CLI):

```bash
cd backend && uv sync --group etl && \
  DATABASE_URL=postgresql://emporio:emporio@localhost:5433/emporio uv run python -m etl
cd ../frontend && DATABASE_URL_UNPOOLED=postgresql://emporio:emporio@localhost:5433/emporio \
  CREATE_USER_PASSWORD='at-least-12-chars' pnpm tsx scripts/create-user.ts <username>
```

As senhas precisam de 12+ caracteres. Sem `CREATE_USER_PASSWORD`, o script pede a senha (ela nunca
é lida do argv). Cinco senhas erradas bloqueiam a conta por 15 minutos.

### Sem Docker

Requisitos: Docker (apenas para o Postgres), [uv](https://docs.astral.sh/uv/), Node 24 com pnpm
(`corepack enable pnpm`).

```bash
docker compose up -d --wait db           # Postgres only, localhost:5433

cd backend
cp .env.example .env                     # DATABASE_URL=...@localhost:5433/emporio
uv sync --group etl
uv run pytest
uv run uvicorn app.main:app --reload     # http://localhost:8000/api/health

cd frontend                              # another terminal
cp .env.example .env.local               # BACKEND_URL=http://localhost:8000, same SERVICE_JWT_SECRET
pnpm install
pnpm dev                                 # http://localhost:3000
```

Para trabalhar na UI sem backend, `CHAT_MODE=mock` no frontend reproduz fixtures fixas (ignorado
em builds de produção, que sempre usam o backend).

### Variáveis de ambiente

Modelos: [`backend/.env.example`](backend/.env.example) e
[`frontend/.env.example`](frontend/.env.example). Segredos nunca são versionados.

| Variável | Onde | Padrão local | Produção |
|---|---|---|---|
| `DATABASE_URL` | ambos | `postgresql://emporio:emporio@localhost:5433/emporio` (`@db:5432` dentro do Docker) | URL pooled do Neon (integração do Vercel Marketplace) |
| `DATABASE_URL_UNPOOLED` | ambos | igual a `DATABASE_URL`; exigida pelo `create-user.ts` | URL direta do Neon, para ETL/DDL e a CLI create-user |
| `SERVICE_JWT_SECRET` | ambos, **mesmo valor** | valor de desenvolvimento no compose | aleatório, 32+ caracteres; assina o token frontend→backend |
| `AUTH_SECRET` | frontend | valor de desenvolvimento no compose | aleatório, 32+ caracteres (sessões do Auth.js) |
| `BACKEND_URL` | frontend | `http://localhost:8000` (`http://backend:8000` no Docker) | injetada pelo service binding do Vercel (`vercel.json`) |
| `CHAT_MODE` | frontend | `backend` (`mock` = fixtures, só em dev) | sempre `backend` |
| `ENVIRONMENT` | backend | `local` | `production` (também detectado via `VERCEL_ENV`) |
| `LLM_PROVIDER`, `ROUTER_PROVIDER` | backend | precisam ser reais para conversar (`openrouter`) | `openrouter` |
| `OPENROUTER_API_KEY` | backend | sua chave | segredo |
| `ROUTER_MODEL`, `SPECIALIST_MODEL`, `GENERAL_MODEL` | backend | veja abaixo | veja abaixo |
| `EMBEDDINGS_PROVIDER`, `GEMINI_API_KEY` | backend | `fake` serve localmente | `gemini` + chave (`fake` é recusado remotamente) |
| `RATE_LIMIT_PER_MINUTE`, `DAILY_TOKEN_BUDGET`, `BUDGET_TIMEZONE` | backend | 20, 200000, `America/Campo_Grande` | igual |
| `MCP_API_KEY` | backend | não definida (`/mcp` desativado) | defina para expor o servidor MCP |

Modelos usados (todos via OpenRouter, uma única chave):

```
ROUTER_MODEL=perplexity/pplx-decider-v1.2
SPECIALIST_MODEL=openai/gpt-6-luna
GENERAL_MODEL=deepseek/deepseek-v4.1-flash
```

Em produção, os dois apps **se recusam a iniciar** quando falta uma variável obrigatória ou um
segredo tem menos de 32 caracteres (fail-closed, spec 004 FR-015): o backend verifica
`SERVICE_JWT_SECRET`, `DATABASE_URL` e a chave do provedor; o frontend verifica `DATABASE_URL`,
`BACKEND_URL`, `AUTH_SECRET` e `SERVICE_JWT_SECRET`.

Execute os cenários de conversa roteirizados (a base das conversas de exemplo):

```bash
cd backend
uv run python -m evals            # fake providers, no keys
uv run python -m evals --live     # real models, needs keys above
```

## Executar em produção

> **Nota de escopo.** O login, o token de serviço assinado (JWT) entre frontend e backend e os
> limites por conta existem porque o plano era um deploy público e aberto, com modelos pagos. O
> projeto agora é executado e demonstrado localmente, onde o `docker compose` já fornece segredos de
> desenvolvimento, então nada disso precisa ser configurado. O deploy na Vercel é mantido como
> documentado, mas não é obrigatório.

Um projeto Vercel usando [Services](https://vercel.com/docs/services) (`vercel.json` na raiz do
repositório): o `frontend` Next.js é o único serviço público; o `backend` FastAPI é privado e é
acessado pelo frontend por um service binding que injeta `BACKEND_URL`. `/mcp` é roteado direto
para o backend. O Postgres é o Neon (região de São Paulo), conectado pelo Vercel Marketplace, que
fornece `DATABASE_URL` e `DATABASE_URL_UNPOOLED`.

**Status: o deploy de produção está falhando no momento e corrigi-lo é o próximo passo.** Desde o
trabalho de autenticação (#44), o frontend se recusa a iniciar sem a configuração obrigatória, e os
logs do deploy mostram `Refusing to start in production with missing required config: BACKEND_URL`.
O que se sabe que falta ou deve ser verificado:

1. `AUTH_SECRET` e `SERVICE_JWT_SECRET` ainda não estão definidos no projeto Vercel (os dois
   serviços precisam do mesmo `SERVICE_JWT_SECRET`); o backend também precisa de
   `ENVIRONMENT=production` e das variáveis do provedor acima.
2. `BACKEND_URL` vem do service binding, então não deve ser definida manualmente. O erro sugere que
   o binding não está visível quando o Next.js executa seu hook de inicialização
   (`src/instrumentation.ts`); a confirmar no próximo deploy e, se for isso, a verificação deve ir
   para o momento da requisição, como o backend já faz.
3. Depois de definir as variáveis, faça um novo deploy: mudanças de variáveis só valem no próximo
   deploy. Em seguida, crie o login do avaliador no Neon com `scripts/create-user.ts`
   (`DATABASE_URL_UNPOOLED` apontando para a URL direta do Neon).

Os deploys são disparados pelo dono do repositório.

## Acesso para avaliadores

Não há página de cadastro: a agente roda em modelos pagos, então o acesso é apenas por conta (spec 004).

- **Localmente (funciona hoje):** `docker compose up --build` com uma chave do OpenRouter em
  `backend/.env`; depois crie seu próprio login com `scripts/create-user.ts`, como mostrado em
  [Executar localmente](#executar-localmente). Essa é toda a configuração.
- **Produção:** quando o deploy for corrigido (veja acima), o usuário e a senha de uma conta pronta
  são enviados junto com o e-mail de entrega, nunca versionados.
- **Sem executar nada:** as cinco transcrições reais em
  [`docs/conversations/`](docs/conversations/) mostram cada chamada de ferramenta e resposta.

## Dados

Os arquivos do desafio em `challenge/` são entradas somente leitura (o `.gitattributes` preserva os
bytes CRLF). Um comando os valida, aplica as regras de correção e carrega o Postgres:

```bash
cd backend
uv run python -m etl            # local database from DATABASE_URL
uv run python -m etl --yes      # required for any non-local host (e.g. Neon)
```

- O seed apaga e recria apenas as tabelas que ele possui, em uma única transação, e imprime antes o
  host de destino. No Neon, defina `DATABASE_URL_UNPOOLED` (endpoint direto); o seed prefere essa
  variável a `DATABASE_URL`.
- Toda anomalia encontrada nos dados, a regra aplicada e as contagens estão em
  [`docs/data-quality-report.md`](docs/data-quality-report.md). O relatório é regenerado pelo seed,
  e o CI falha se a cópia versionada estiver desatualizada.
- O seed também constrói o índice de busca: trechos de políticas do PDF e um documento por produto,
  com embeddings do Gemini (`EMBEDDINGS_PROVIDER=gemini`, `GEMINI_API_KEY`) e uma coluna de busca
  textual. `EMBEDDINGS_PROVIDER=fake` (offline, determinístico) é recusado para destinos remotos e
  produção. Os vetores ficam em cache em `embedding_cache`, então recarregar o seed não faz chamadas.
  Plano gratuito do Gemini: 100 requisições/min, 1.000 requisições/dia, 30 mil tokens/min; o Google
  pode usar o conteúdo do plano gratuito para melhorar seus produtos, o que não é problema para
  estes dados fictícios.
- Design: [`specs/001-data-foundation/`](specs/001-data-foundation/).

## Decisões principais e trade-offs

O contexto completo, as alternativas e a justificativa de cada decisão estão em
[`docs/decision-log.md`](docs/decision-log.md) (a partir da DL-001). Resumo das decisões que o
enunciado pede para justificar:

| Decisão | Escolha | Por quê (veja o decision log para as alternativas) |
|---|---|---|
| Framework / abordagem | Roteador de intenção (Python puro) + uma execução de `langchain.agents.create_agent` por requisição, ferramentas por function calling, RAG híbrido para políticas | Um framework de grafo não acrescenta nada quando o roteamento em si não é transmitido em streaming (DL-011); function calling mantém os fatos determinísticos (constituição I); o RAG escala além do manual atual de 8 páginas |
| LLM e provedor | OpenRouter, uma chave para todos os modelos: `perplexity/pplx-decider-v1.2` (roteador/decider), `openai/gpt-6-luna` (respostas especialistas), `deepseek/deepseek-v4.1-flash` (geral/ambíguo) | Medido com um spike de roteador de 34 cenários e evals reais de 27-29/29 (DL-012); um único provedor simplifica os segredos em comparação a misturar Anthropic + uma API de decider dedicada |
| Arquitetura de recuperação | Busca textual do Postgres (`pt_unaccent`) + pgvector, combinadas com RRF k=60; embeddings Gemini `gemini-embedding-001`, 768 dimensões | A busca textual com semântica OR mantém a cobertura para perguntas em linguagem natural sem ajustes; uma correspondência por prefixo em lexemas longos corrige uma falha do stemmer que os testes de consultas de referência detectaram (DL-010) |
| Estratégia de prompt | O prompt de sistema traz a data/hora atual da loja e a persona (Melody, manual §7.1/§7.2); as saídas das ferramentas são a única fonte de fatos, explicitamente delimitadas como "FATOS SOMENTE DAS FERRAMENTAS" contra prompt injection | Verificada pelos cenários de segurança US5 (extração de prompt, descontos inventados, funcionário falso) |
| Interface de interação | Chat web: Next.js (App Router) + Vercel AI SDK `useChat`, tokens em streaming, linhas de status das ferramentas e cards de produto; alternância PT/EN, tema claro/escuro, mobile-first. As mesmas ferramentas também são expostas via MCP | O canal do cliente em uma loja é uma janela de chat; a UI é um cliente fino que só renderiza o que o backend Python transmite (sem regra de negócio, sem fatos derivados na UI), então Python continua sendo a linguagem principal, como o enunciado exige. O MCP mostra que as ferramentas são reutilizáveis por outros agentes |
| Persistência do histórico de conversa | Por navegador: o id da conversa e suas últimas 40 mensagens ficam no `localStorage`, sobrevivem a um reload e são apagados por "Nova conversa" ou ao sair. Cada requisição leva a janela recente (12 mensagens) a uma API sem estado; o único estado no servidor é a verificação de pedido por conversa | Suficiente para um chat de suporte (um reload não perde mais o contexto nem a verificação do pedido) sem infraestrutura nova. Histórico durável entre dispositivos (checkpointer no Postgres) é um P1 (#12/S7) e não é necessário para o enunciado (DL-FE-003) |
| Controle de acesso e limites de custo | Login com usuário/senha (Auth.js, contas só via CLI, sem cadastro), token HS256 de curta duração do frontend para o backend, 20 requisições/min e 200 mil tokens/dia por conta, verificações de configuração fail-closed | A agente roda em modelos pagos atrás de uma URL pública; o avaliador do enunciado precisa de um login, não de acesso aberto (spec 004, DL-BE-002, DL-FE-001) |
| Respostas sobre estoque | As ferramentas devolvem o `stock_quantity` exato; `get_product(quantity=N)` devolve `enough_stock` calculado em Python | A agente precisa dizer com certeza se N unidades estão disponíveis, nunca mandar o cliente conferir (DL-BE-003) |
| Execução local | Docker Compose com Postgres, backend e frontend; o backend lê `backend/.env` para a chave do provedor | Quem clona o repositório roda tudo com um comando e uma chave |
| Tratamento dos dados | ETL determinístico com regras de correção documentadas por anomalia (`docs/data-quality-report.md`), sem limpeza silenciosa | O enunciado destaca explicitamente as anomalias registradas; um agente de atendimento não deve mascarar uma data errada ou um registro de produto contraditório sem uma regra visível |

## Premissas

Onde o enunciado ou os dados foram omissos, foram adotadas estas interpretações (cada uma tem uma
entrada no decision log com o raciocínio):

- **"Hoje" é a data real atual** em Campo Grande (America/Campo_Grande). Os prazos de devolução e o
  "aberto agora" são calculados a partir dela, então todo pedido do dataset está fora do prazo de
  devolução; a lógica das políticas continua comprovada por uma suíte de evals com relógio
  roteirizado (DL-002, DL-013).
- **A agente informa, não vende.** Ela nunca faz pedidos nem reservas; indica o site, a loja ou o
  WhatsApp. Ela pode registrar uma solicitação de devolução, uma reclamação ou um encaminhamento
  para um humano, e somente a pedido explícito do cliente.
- **A loja vende apenas instrumentos.** Acessórios (cordas, palhetas, cabos, cases, pedais,
  amplificadores) são recusados com educação, sugerindo um instrumento no lugar.
- **Dados de pedido exigem comprovação de titularidade:** o e-mail ou telefone cadastrado (com ou
  sem o número do pedido), com erro genérico em caso de divergência e bloqueio após falhas
  repetidas (privacidade, manual §9). O nome do cliente sozinho ("sou a Fernanda…") nunca é prova;
  ele só desambigua um e-mail compartilhado por dois clientes.
- **O que significam os status de pedido:** `pending` = recebido, aguardando confirmação do
  pagamento; `confirmed` = pago, aguardando envio; `shipped`, `delivered`, `cancelled` conforme o
  nome. Os dados não têm timestamps de status, então "há quanto tempo" é contado a partir da data do
  pedido; pedidos pendentes ou confirmados há mais de 7 dias são sinalizados com oferta de
  atendimento humano.
- **O calendário de promoções (§6.1) é uma faixa, não uma promessa:** "melhor época para comprar"
  compara as faixas das campanhas (Black Friday 15–30%, aniversário da loja 10–25%…) e mostra o que
  está em promoção agora; nenhum desconto futuro é prometido para um produto específico.
- **Anomalias dos dados são corrigidas por regras explícitas, não silenciosamente** (por exemplo, o
  nome do produto prevalece sobre uma descrição contraditória; apenas quatro promoções estão ativas),
  listadas em `docs/data-quality-report.md` (DL-001).
- **As respostas seguem o idioma do cliente** (português por padrão, com suporte a inglês e
  espanhol); o manual de políticas é pesquisado em português.
- **O acesso é por conta e o uso é limitado** (20 mensagens/min, 200 mil tokens/dia por conta),
  porque a agente publicada roda em modelos pagos atrás de uma URL pública.
- **As respostas sobre estoque são exatas:** a agente informa a quantidade em estoque e se N
  unidades podem ser vendidas, a partir do banco de dados (DL-BE-003).
- **"Em breve" significa pré-venda:** esse produto é oferecido normalmente (preço, formas de
  pagamento) com um aviso claro de que não há entrega imediata e de que chega em breve; nenhuma data
  de chegada é inventada. Comprá-lo é uma compra entregue mais tarde, não uma reserva (o manual não
  prevê reservas). Por isso o produto 130 nos pedidos 3 e 14 não é tratado como anomalia (DL-BE-006).

## Fluxo de trabalho com assistente de IA

Este projeto foi construído com o **Claude Code**, e esse uso é parte da entrega: o enunciado pede
que o fluxo de trabalho seja explicado, não apenas o fato de que houve uso de IA.

- **Desenvolvimento orientado a especificação.** Todo épico passa pelo [Spec
  Kit](https://github.com/github/spec-kit) (skills `speckit-*`): `spec.md` → `plan.md` →
  `tasks.md` em `specs/NNN-*/`, conferidos contra a
  [`.specify/memory/constitution.md`](.specify/memory/constitution.md) (por exemplo, "fatos são
  calculados em Python, nunca pelo LLM") antes de qualquer código ser escrito. Nenhuma tarefa de
  implementação começa sem uma spec e um plano aprovados.
- **Portão de dois revisores.** Toda spec e todo PR de código passa por uma revisão de QA e uma de
  engenheiro sênior (ambas executadas como subagentes do Claude Code, instruídos a encontrar
  defeitos reais, não a carimbar) antes de o dono do projeto fazer o merge. As revisões são
  postadas como um comentário consolidado no PR; os achados e as correções aplicadas (ou
  explicitamente adiadas) ficam registrados no decision log — veja, por exemplo, "Review of PR 1"
  na DL-012 ou "QA checked the facts against the CSVs and fixed two scenarios the data cannot
  support" na DL-011.
- **Worktrees paralelas.** Trilhas independentes (dados/ETL, núcleo do agente, ações, UI do chat,
  documentação) rodam em git worktrees/branches separadas, cada uma com sua própria sessão do Claude
  Code e limitada aos próprios arquivos por um briefing curto (a trilha deste README era "mexer só
  em docs e README"). É por isso que o decision log usa prefixos por área (`DL-BE-`, `DL-FE-`,
  `DL-DOCS-`, `DL-DATA-`) depois que a numeração saiu de uma sequência única, para evitar colisões
  entre branches trabalhando ao mesmo tempo.
- **O que a IA fez e o que a pessoa decidiu.** Cada entrada do decision log termina com uma linha
  "Role of AI". O padrão recorrente: o Claude Code redigiu specs/planos/código, fez pesquisa
  (versões de bibliotecas, peculiaridades de APIs verificadas em um venv descartável) e executou as
  duas revisões; o dono do projeto tomou as decisões de modelo/arquitetura/escopo e fez todos os
  merges. Um exemplo concreto: DL-011 — o Claude Code redigiu o plano e a pesquisa do núcleo do
  agente, mas a divisão em 3 PRs e a escolha dos modelos foram do dono; o subagente revisor sênior
  encontrou três armadilhas da API do LangGraph (verificadas empiricamente) antes de a implementação
  começar.
- **Nunca atribuído nos commits.** Conforme o acordo de trabalho, nenhum commit, PR ou issue
  menciona o Claude ou a ajuda de IA, e não há trailers `Co-Authored-By` — todo o uso de IA está
  documentado aqui e em `docs/decision-log.md`, de modo que o histórico de commits se lê como o
  histórico de um projeto comum, enquanto o fluxo de trabalho com IA é totalmente divulgado nos
  documentos que o enunciado pede.

## Servidor MCP

A Melody chama suas ferramentas em processo; o MCP é uma porta lateral opcional para que **outros**
clientes de IA (por exemplo, o Claude Desktop) reutilizem as mesmas ferramentas de catálogo e
políticas. Apenas as ferramentas **somente leitura** são expostas (`search_products`, `get_product`,
`find_similar_products`, `get_active_promotions`, `calculate_payment_options`, `search_policies`,
`get_store_info`). Consultas de pedido e ações (devoluções, reclamações, encaminhamento) exigem um
cliente verificado e não estão disponíveis via MCP (DL-BE-007).

Ele fica em `/mcp`, atrás de uma chave bearer (`MCP_API_KEY`; desativado quando não definida), e não
contém regra de negócio (`backend/app/mcp.py` apenas envolve as funções de `backend/app/tools/`).

Localmente, defina `MCP_API_KEY=dev-key` em `backend/.env`, reinicie o backend e adicione isto ao
`claude_desktop_config.json` do Claude Desktop (ou a qualquer cliente MCP com HTTP streamable e
header bearer):

```json
{
  "mcpServers": {
    "emporio-da-musica": {
      "url": "http://localhost:8000/mcp",
      "headers": { "Authorization": "Bearer dev-key" }
    }
  }
}
```

## Limitações e próximos passos

O que se sabe que está incompleto ou fraco, e o que seria feito com mais tempo (o detalhe completo e
as notas de risco residual estão no decision log, por exemplo DL-011 "Residual risk" e DL-012 "Not
applied, on purpose"):

- **O histórico é por navegador.** A conversa sobrevive a um reload, mas não a uma troca de
  dispositivo ou navegador; histórico no servidor é um P1 (#12/S7, checkpointer no Postgres).
- **O deploy de produção está fora do ar** (veja [Executar em produção](#executar-em-produção));
  a stack completa roda localmente com Docker.
- **O orçamento é flexível sob concorrência.** Duas requisições simultâneas podem passar pela
  verificação diária de tokens antes de qualquer uma registrar o uso, então uma conta pode exceder
  brevemente 200 mil tokens; o limite por minuto restringe o excesso (documentado em
  `specs/004-auth-limits-deploy/contracts/`).
- **Sem confirmação com humano no circuito antes de uma ação de escrita** (`request_return`,
  `register_complaint`) além de o modelo perguntar ao cliente na própria conversa; um portão
  `interrupt` rígido está planejado (P1, #13/S9).
- **Ainda sem tracing/observabilidade de custo em produção** (P1, #15/S10, Langfuse).
- **O MCP é somente leitura e apenas local**: sem ferramentas de pedido ou de ação via MCP, e a
  demo com o Claude Desktop (#19) não foi gravada.
- **Os cenários de prazo de devolução usam a data real atual**, então todo pedido do dataset está
  fora do prazo de devolução hoje por construção (os pedidos são anteriores ao desafio); é uma
  escolha deliberada e documentada (DL-002) em vez de uma data de referência configurável, com uma
  suíte de evals com relógio roteirizado para ainda comprovar a lógica das políticas (DL-013).
- **As conversas de exemplo foram gravadas dirigindo a API manualmente**, não exportadas pelo
  runner de evals; uma flag `--export` as tornaria regeneráveis com um comando.
- **Com mais tempo:** evals com LLM-as-judge sobre o conjunto de cenários (P2, #22/S18) e o
  dashboard administrativo de insights (P2, #21/E16). O notebook de EDA com os achados de qualidade
  de dados já está em `analysis/` (#22/S17).
