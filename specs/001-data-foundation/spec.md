# Feature Specification: Data Foundation

**Feature Branch**: `001-data-foundation`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Data foundation (epic #5): reproducible ETL that validates the challenge CSVs, applies the DL-002 correction rules, normalizes text to NFC, and loads the store database (catalog, orders, order items, customers, promotions); generates docs/data-quality-report.md listing every anomaly, rule applied and counts; chunks the policy PDF per section (number/title metadata) and indexes products (name + specs, + description except IDs 135–144) with Portuguese full-text + vector search; embeddings behind an interface (real provider | deterministic fake), query-embedding cache, full-text fallback when the embeddings provider fails; seed command works against any database URL (local and production)."

**Source of truth**: GitHub issue #5 (scope and acceptance criteria), DL-001 (findings), DL-002 (correction rules).

## Clarifications

### Session 2026-10-31

- Q: The committed customers.csv already stores every "Ponta Porã" in NFC; how is the NFC criterion met? → A: Keep NFC normalization, test it with a synthetic decomposed (NFD) fixture; the report shows the real count (0 in the current data) and the decision log corrects DL-001 (both values are already NFC; the profiling split them because of a trailing `\r`: the CSVs use CRLF and the last row has no trailing newline).
- Q: What may the seed do to a database shared with other epics' tables? → A: It touches only the tables it owns (store data, search indexes, report data): create if missing, then truncate and reload them in a single transaction. Other tables are never touched. The query-embedding cache is kept across seeds.
- Q: What happens if the real embeddings provider fails during seeding? → A: Retry with backoff; if it still fails, abort and roll back so nothing is committed. Query-time fallback to full-text covers runtime outages.
- Q: Where does the query-embedding cache live? → A: In a database table keyed by provider, model and normalized query, so it survives serverless cold starts and is shared across instances. A small in-process cache may sit in front.

## User Scenarios & Testing *(mandatory)*

The "users" of this feature are (a) the developer/operator who seeds an environment, (b) the
agent tools built in later epics, which read clean facts and search the policy manual and the
catalog, and (c) the challenge evaluator, who reads the data quality report.

### User Story 1 - Seed a clean, trustworthy store database (Priority: P1)

An operator runs one seed command against a target database. The command reads the read-only
challenge files, validates every row, applies the documented correction rules, normalizes text,
and loads catalog, customers, orders, order items and promotions. Running it again yields the
exact same database.

**Why this priority**: every agent tool (price, stock, order status, promotion) depends on these
facts being correct. Without it nothing downstream can be built or tested.

**Independent Test**: run the seed against an empty database twice; check row counts, per-table
checksums and the rule-specific facts listed below.

**Acceptance Scenarios**:

1. **Given** an empty database, **When** the seed runs, **Then** it loads 9 categories, 65 products, 50 customers, 20 orders, 22 order items and 25 promotions, and exits successfully.
2. **Given** order 3 (stored total 3450, items sum 3498) and order 20 (stored total 1400, items sum 1488), **When** loaded, **Then** each keeps its original total and is flagged as a total mismatch with the computed items sum recorded.
3. **Given** products 135–144, whose descriptions contradict their names/specs, **When** loaded, **Then** the name and specs are authoritative and the description is marked untrusted (not to be shown to customers).
4. **Given** product 96 (two inactive promotions, 18% and 40%, and stock 0), **When** loaded, **Then** it has no effective promotion and is unavailable.
5. **Given** a product with several active promotions, **When** the effective promotion is resolved, **Then** the largest active discount applies; inactive promotions never apply.
6. **Given** products 113 and 136 (`discontinued`, 136 with 13 units), **When** loaded, **Then** both are not sellable regardless of stock.
7. **Given** product 130 (`coming_soon`, referenced by orders 3 and 14), **When** loaded, **Then** it is marked "coming soon" and not sellable, and the order references are kept and flagged.
8. **Given** customer text in different Unicode forms (a fixture with "Ponta Porã" both decomposed and composed), **When** loaded, **Then** all text is stored in NFC and both values compare equal. The report shows how many values were normalized in the real data (currently 0).
9. **Given** customers 11 and 43 sharing `bruno.martins@jmail.com`, **When** loaded, **Then** both customers are kept and the shared email is flagged.
10. **Given** a database already seeded, **When** the seed runs again, **Then** row counts and per-table checksums are identical to the first run.

---

### User Story 2 - Data quality report (Priority: P1)

After every seed, a human-readable report is regenerated listing every anomaly found, the rule
applied to it, the affected record IDs and counts per anomaly type.

**Why this priority**: handling the deliberate inconsistencies explicitly is part of the
evaluation (constitution principle III); the report is the evidence.

**Independent Test**: run the seed; compare the generated report against the expected anomaly
list from DL-001.

**Acceptance Scenarios**:

1. **Given** the challenge dataset, **When** the seed runs, **Then** `docs/data-quality-report.md` lists each anomaly type with its rule, affected IDs and count, matching DL-001.
2. **Given** two seed runs on the same input, **When** both reports are compared, **Then** they are identical (no timestamps or ordering differences in the body).
3. **Given** a row that fails schema validation, **When** the seed runs, **Then** the run fails with a message naming the file, row and field, and nothing is partially loaded.

---

### User Story 3 - Search the policy manual (Priority: P1)

Agent tools search the store policy manual and get back the relevant section(s), each with its
section number and title, so answers can cite "§4.1".

**Why this priority**: policy questions (returns, shipping, warranty, payment) are a core part of
the challenge; retrieval quality drives answer quality.

**Independent Test**: index the manual with the deterministic fake embedder; run fixed queries
and check the top results.

**Acceptance Scenarios**:

1. **Given** the indexed manual and the deterministic fake embedder, **When** searching "posso devolver meu pedido?", **Then** §4.1 (Direito de Arrependimento) is in the top 3 results.
2. **Given** the real embeddings provider (opt-in test run), **When** searching English and Spanish variants of the same question, **Then** §4.1 is in the top 3 results.
3. **Given** the embeddings provider is unavailable or errors, **When** searching, **Then** results are still returned using full-text search only, and the degradation is logged.
4. **Given** the same query is searched twice, **When** the second search runs, **Then** its embedding is served from the cache without calling the provider.

---

### User Story 4 - Search the product catalog (Priority: P2)

Agent tools search products by meaning and keywords ("violão para iniciante com captação") over
name, specs and trusted descriptions, to support lookups and "similar product" suggestions.

**Why this priority**: needed by the product and recommendation tools in the agent epic, but the
policy index is the harder retrieval case and is validated first.

**Independent Test**: index products with the fake embedder; check that untrusted descriptions are
absent from indexed text and that a name query returns the product.

**Acceptance Scenarios**:

1. **Given** products 135–144, **When** the catalog index is built, **Then** no description text from those products appears in indexed text or embeddings input.
2. **Given** product "Yamaha C40 Nylon Natural", **When** searching "Yamaha C40", **Then** it is the top result.

---

### User Story 5 - Seed any environment (Priority: P2)

The same seed command targets the local database or the production database, selected only by
the configured database URL.

**Why this priority**: required to deploy (epic 004), but local seeding unblocks all other work.

**Independent Test**: run the seed against the production database URL and check row counts.

**Acceptance Scenarios**:

1. **Given** a production database URL, **When** the seed runs, **Then** it succeeds with the same row counts and checksums as locally.
2. **Given** no database URL configured, **When** the seed runs, **Then** it fails fast with a clear message.

### Edge Cases

- Policy text contains contradictions (two WhatsApp numbers in §1.2 vs §7; installment table vs §3.1; email with and without accent): the manual is indexed as written; the conflicts are listed in the report with the authoritative value per DL-002 (§1.2 contact, unaccented email, §3.1 installments).
- Product `specs` JSON has different keys per category (4 schemas): each category's schema is validated; unknown or missing keys fail validation.
- Duplicate promotions per product (93, 96, 99): all rows kept; resolution picks the effective one.
- An order item references a non-sellable product (130 in orders 3 and 14): kept and flagged, never dropped.
- Embedding provider rate limit or failure during seeding: retried with backoff, then the seed aborts with store tables unchanged (FR-023).
- Another feature's table has a foreign key to an owned table: the seed fails rather than emptying that table (FR-020).
- Re-seeding production while other epics' tables (users, chat history, token usage) exist: those tables are untouched (FR-020).
- The source CSVs use CRLF line endings and the last row has no trailing newline: parsed values never carry a trailing `\r`, and the last row is read like any other (DL-001 correction).

## Requirements *(mandatory)*

### Functional Requirements

**Ingestion and validation**

- **FR-001**: The system MUST read the challenge CSVs and policy PDF from `challenge/` without modifying them.
- **FR-002**: The system MUST validate every row against a typed schema (types, required fields, allowed status/payment values, referential integrity between orders, items, customers, products, categories and promotions) before loading anything.
- **FR-003**: On any validation error the system MUST abort with a message naming file, row and field, leaving the target database unchanged.
- **FR-004**: The system MUST normalize all text fields to Unicode NFC before storing, comparing or indexing.

**Correction rules** (each one an explicit, separately tested rule, per DL-002)

- **FR-005**: Order total mismatch: keep the original `total_brl`; record the computed items sum and flag the order.
- **FR-006**: Name vs description: name is authoritative; descriptions of products 135–144 are marked untrusted and excluded from customer-facing text and from search indexing.
- **FR-007**: Specs vs description: specs are authoritative.
- **FR-008**: Promotions: only active promotions apply; when several are active for one product, the largest discount is the effective one; the system MUST expose an effective-promotion per product.
- **FR-009**: Sellability: `discontinued` is never sellable; `active` with stock 0 is unavailable; `coming_soon` is shown as coming soon and not sellable. The system MUST expose a derived availability per product.
- **FR-010**: Customers sharing an email are kept and flagged.
- **FR-011**: Policy conflicts (contact numbers, email spelling, installment table) and the missing purchase channel on orders (the withdrawal right applies only to online purchases) MUST be recorded with the authoritative value per DL-002.

**Report**

- **FR-012**: Each seed MUST regenerate `docs/data-quality-report.md` with, per anomaly type: description, rule applied, affected IDs, count. Output MUST be deterministic.

**Retrieval index**

- **FR-013**: The policy manual MUST be split into one chunk per numbered section (subsections such as 4.1 are their own chunks), each with section number, title and parent section.
- **FR-014**: Products MUST be indexed with name, category and specs, plus description only when trusted.
- **FR-015**: Both indexes MUST support Portuguese full-text search and vector similarity search, combined into one hybrid ranking.
- **FR-016**: Embeddings MUST be produced through a provider interface with a real implementation and a deterministic fake (no network, same input → same vector); the provider is selected by configuration.
- **FR-017**: Query embeddings MUST be cached in a database table keyed by provider, model and normalized query text (NFC, casefolded, whitespace collapsed and trimmed), so the cache survives cold starts and is shared across instances. Seeding MUST NOT clear this cache.
- **FR-018**: If the embeddings provider fails at query time, search MUST fall back to full-text only and log the degradation.
- **FR-019**: Re-seeding MUST NOT re-embed unchanged content (embeddings keyed by content hash), to stay within the provider's free tier.

**Operation**

- **FR-020**: A single seed command MUST build schema, load data, build indexes and write the report, against the database given by the configured URL. It MUST only create, truncate and reload the tables it owns, in a single transaction, and MUST NOT touch any other table.
- **FR-021**: The seed MUST be idempotent: two runs produce the same row counts and the same per-table checksums.
- **FR-022**: Secrets (database URL, embeddings API key) MUST come only from environment variables.
- **FR-023**: If the embeddings provider fails during seeding, the seed MUST retry with backoff and then abort with the store and index tables unchanged (embeddings are computed before the write transaction opens); it MUST NOT commit a partially embedded index or substitute the fake embedder.

### Key Entities

- **Category**: product family (9); name and description.
- **Product**: ID, name, category, price, stock, status, category-specific specs, description, description-trusted flag, derived availability, effective promotion.
- **Promotion**: product, discount percent, label, active flag; several per product possible.
- **Customer**: ID, name, phone, email, city (NFC); shared-email flag.
- **Order**: ID, customer, date, status, payment method, original total, computed items sum, mismatch flag, tracking code, estimated delivery, notes.
- **Order item**: order, product, quantity; flagged when product is not sellable.
- **Policy chunk**: section number, title, parent section, text, full-text vector, embedding.
- **Product search document**: product, indexed text, full-text vector, embedding.
- **Data anomaly**: type, rule, affected record IDs, count — the source of the report.
- **Query embedding cache entry**: normalized query, provider/model, vector.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh environment is fully seeded (data + indexes + report) with one command in under 2 minutes with the real embeddings provider and under 30 seconds with the fake.
- **SC-002**: 100% of the anomalies listed in DL-001 appear in the report with rule and counts; every correction rule has at least one dedicated test.
- **SC-003**: Two consecutive seeds produce identical row counts, table checksums and report content.
- **SC-004**: "posso devolver meu pedido?" returns §4.1 in the top 3 with the fake embedder (in CI), and EN/ES variants do the same with the real provider.
- **SC-005**: With the embeddings provider down, policy search still returns results (full-text) for 100% of the reference queries (a fixed set of at least 5 questions covering returns, shipping, installments, warranty and contact).
- **SC-006**: Zero description text from products 135–144 appears in indexed text or embedding inputs.
- **SC-007**: The seed succeeds against the production database and leaves tables owned by other features unchanged.

## Assumptions

- The database and backend scaffolding come from issue #3; this feature adds data and indexes on top.
- Seeding is a full rebuild of the store tables (data set is tiny: under 200 rows); embeddings are reused by content hash.
- Product 130 appearing in orders is historical data and is preserved; it is flagged, not corrected.
- The real clock is used elsewhere; this feature does not compute dates or eligibility.
- Price, stock, discount and availability values computed here are exposed for deterministic tools; final price calculation per payment method belongs to the agent epic.
- The manual is in Portuguese; cross-language retrieval relies on the multilingual real embeddings provider (the fake embedder only guarantees the Portuguese CI case).
