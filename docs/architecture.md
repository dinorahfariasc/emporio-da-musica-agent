# Architecture diagrams

Mermaid diagrams (rendered by GitHub). Português: `README.pt-BR.md` embeds the same diagrams.

## 1. Containers

```mermaid
flowchart LR
    user([Customer]) --> web["Next.js frontend<br/>chat UI, login (Auth.js),<br/>/api/chat as BFF"]
    web -->|"SSE stream<br/>service JWT"| api["FastAPI backend<br/>/api/chat"]
    api --> agent["Agent<br/>router + create_agent<br/>(LangChain/LangGraph)"]
    agent --> tools["Tools<br/>plain Python,<br/>facts computed here"]
    tools --> db[("Postgres + pgvector<br/>store tables, search index,<br/>limits, conversation state")]
    agent -.->|chat + router models| or["OpenRouter"]
    tools -.->|query embeddings| gem["Gemini embeddings"]
    ext([External MCP client]) -->|"bearer key<br/>read-only tools"| mcp["/mcp"]
    mcp --> tools
```

## 2. One chat turn

```mermaid
sequenceDiagram
    actor C as Customer
    participant W as Next.js /api/chat
    participant B as FastAPI /api/chat
    participant R as Router (decider)
    participant A as Agent (create_agent)
    participant T as Tools
    participant D as Postgres
    C->>W: message (+ recent history)
    W->>W: check session, sign short-lived JWT
    W->>B: POST with JWT
    B->>D: rate limit and daily token budget
    B->>R: classify intent
    R-->>B: intent + confidence
    B->>A: run with the tools for that intent
    loop while the model needs facts
        A->>T: tool call
        T->>D: parameterized SQL / hybrid search
        D-->>T: rows
        T-->>A: JSON result
    end
    A-->>B: token and tool events
    B-->>W: SSE (AI SDK UI message stream)
    W-->>C: streamed answer + product cards
    B->>D: record token usage
```

## 3. Fact or policy? Who answers

```mermaid
flowchart TD
    q[Customer message] --> i{Intent}
    i -->|price, stock, promotion| t1["Deterministic tools<br/>get_product, calculate_payment_options,<br/>get_active_promotions"]
    i -->|returns, hours, payment rules| t2["search_policies<br/>(RAG over the manual)<br/>+ Python rules for deadlines"]
    i -->|order status| v{"Order number +<br/>owner's e-mail or phone?"}
    v -->|yes| t3[get_order_status]
    v -->|no, or mismatch| deny["Generic refusal,<br/>lockout after repeated failures"]
    i -->|return, complaint, human| act["check_return_eligibility,<br/>then action tools only on<br/>explicit customer request"]
    i -->|out of scope| out["Polite decline,<br/>offer instruments"]
    t1 --> w[LLM writes the answer from tool results only]
    t2 --> w
    t3 --> w
    act --> w
```

## 4. Data and retrieval

```mermaid
flowchart LR
    csv["CSVs (inputs/data)"] --> etl["ETL<br/>validation + explicit<br/>correction rules"]
    pdf["Policies PDF"] --> chunk["Chunks per section<br/>(§ number kept)"]
    etl --> pg[("Postgres")]
    etl --> report["data-quality-report.md"]
    chunk --> idx["Search index<br/>full-text (pt_unaccent)<br/>+ Gemini vectors, cached"]
    etl --> idx
    idx --> pg
    q[Query] --> ft[Full-text rank]
    q --> vec[Vector rank]
    pg --> ft
    pg --> vec
    ft --> rrf["Reciprocal Rank Fusion (k=60)"]
    vec --> rrf
    rrf --> hits[Top hits]
```

## 5. Semantic recommendation

```mermaid
flowchart TD
    m["'Soft guitar for a beginner, up to R$ 700'"] --> p["Prompt: translate to<br/>description + category_id + max_price_brl"]
    p --> f["find_similar_products"]
    f --> s["Hybrid search<br/>filters: category, sellable, price"]
    s --> v["Cards from the database:<br/>price, stock, specs"]
    v --> a["Answer cites one shared trait<br/>and one difference, from tool data only"]
```

## 6. AI core: which model runs when

Router decides the path; the specialist gets only the tools of its intent, the general model gets all of them. Embeddings only run inside a free-text search.

```mermaid
flowchart TD
    msg(["Customer message + last 12 messages"]) --> rt["1. ROUTER<br/>perplexity/pplx-decider-v1.2<br/>returns intent + confidence"]
    rt -.->|"fails or takes over 2.5 s"| fb["Fallback: structured output<br/>from the specialist model"]
    fb -.-> dec
    rt --> dec{"Confidence ≥ 0.75 and a single intent?"}
    dec -->|yes| sp["2a. SPECIALIST<br/>openai/gpt-6-luna<br/>prompt + ONLY the tools of that intent"]
    dec -->|"no: multi_intent, unclear, router down"| ge["2b. GENERAL<br/>deepseek/deepseek-v4.1-flash<br/>generic prompt + ALL tools"]
    sp --> loop
    ge --> loop
    loop{"Model needs a fact?"} -->|yes, up to 8 steps| tl["3. TOOLS (Python)<br/>price, stock, installments, deadlines,<br/>order lookup: deterministic SQL and rules"]
    tl --> srch{"Free-text search?"}
    srch -->|yes| emb["4. EMBEDDINGS<br/>gemini-embedding-001<br/>embeds only the query"]
    emb --> hy["Hybrid search: full-text + vector, fused by RRF"]
    srch -->|no| db[("Postgres")]
    hy --> db
    db --> loop
    loop -->|no| ans["Answer written ONLY from tool results"]
    ans --> out(["Streamed to the customer"])
```

## 7. Worked example

A subjective request, from message to answer:

```mermaid
sequenceDiagram
    actor C as Customer
    participant R as Router (pplx-decider)
    participant S as Specialist (gpt-6-luna)
    participant T as Tool find_similar_products
    participant E as Embeddings (gemini)
    participant D as Postgres
    C->>R: "I want a soft guitar for a beginner, up to R$ 700"
    R-->>S: intent product_search, confidence 0.93 (≥ 0.75)
    Note over S: Prompt for product_search + 2 tools only (search_products, find_similar_products)
    S->>T: description="soft, beginner", category_id=5, max_price_brl=700
    T->>E: embed the description
    E-->>T: 768-dim vector
    T->>D: full-text + vector search, filters: category 5, sellable, price ≤ 700
    D-->>T: top 3 with price and stock
    T-->>S: JSON
    S-->>C: Answer: one shared trait + one difference, prices from the JSON
    Note over C,D: Price and stock come from the database, the model only words the answer. Embeddings are used only to understand the query, never to state facts.
```

