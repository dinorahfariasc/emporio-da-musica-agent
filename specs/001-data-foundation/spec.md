# Feature Specification: Data Foundation

**Feature Branch**: `001-data-foundation`

**Created**: 2026-10-31

**Status**: Draft (revised after the PR #27 QA + senior review: scope cut to 2 implementation PRs)

**Input**: User description: "Data foundation (epic #5): reproducible ETL that validates the challenge CSVs, applies the DL-002 correction rules, normalizes text to NFC, and loads the store database (catalog, orders, order items, customers, promotions); generates docs/data-quality-report.md listing every anomaly, rule applied and counts; chunks the policy PDF per section (number/title metadata) and indexes products (name + specs, + description except IDs 135–144) with Portuguese full-text + vector search; embeddings behind an interface (real provider | deterministic fake), query-embedding cache, full-text fallback when the embeddings provider fails; seed command works against any database URL (local and production)."

**Source of truth**: GitHub issue #5 (scope and acceptance criteria), DL-001 (findings), DL-002 (correction rules).

## Clarifications

### Session 2026-10-31

- Q: The committed customers.csv already stores every "Ponta Porã" in NFC; how is the NFC criterion met? → A: Keep NFC normalization, test it with a synthetic decomposed (NFD) fixture; the report shows the real count (0 in the current data) and the decision log corrects DL-001 (both values are already NFC; the profiling split them because of a trailing `\r`: the CSVs use CRLF and the last row has no trailing newline).
- Q: What may the seed do to a database shared with other epics' tables? → A: It touches only the tables it owns: in a single transaction it drops and recreates them (no `CASCADE`) and reloads them. Other tables are never touched. The embedding cache is kept across seeds.
- Q: What happens if the real embeddings provider fails during seeding? → A: Retry, honouring the provider's `Retry-After`; if it still fails, abort with the database unchanged. Query-time fallback to full-text covers runtime outages.
- Q: Where does the query-embedding cache live? → A: In a database table keyed by provider, model and normalized query, so it survives serverless cold starts and is shared across instances.

## User Scenarios & Testing *(mandatory)*

The "users" of this feature are (a) the developer/operator who seeds an environment, (b) the
agent tools built in later epics (#6), which read clean facts and search the policy manual and
the catalog, and (c) the challenge evaluator, who reads the data quality report.

Delivery: **PR A** = US1 + US2 + US5 safety (store data, report, safe seed command).
**PR B** = US3 + US4 + production seed (retrieval).

### User Story 1 - Seed a clean, trustworthy store database (Priority: P1) · PR A

An operator runs one seed command against a target database. The command reads the read-only
challenge files, validates every row, applies the documented correction rules, normalizes text,
and loads catalog, customers, orders, order items and promotions. Running it again yields the
exact same database.

**Why this priority**: every agent tool (price, stock, order status, promotion) depends on these
facts being correct. Without it nothing downstream can be built or tested.

**Independent Test**: run the seed against an empty local database twice; check row counts,
per-table checksums and the rule-specific facts listed below.

**Acceptance Scenarios**:

1. **Given** an empty database, **When** the seed runs, **Then** it loads 9 categories, 65 products, 50 customers, 20 orders, 22 order items and 25 promotions, and exits successfully.
2. **Given** order 3 (stored total 3450, items sum 3498) and order 20 (stored total 1400, items sum 1488), **When** loaded, **Then** each keeps its original total and is flagged as a total mismatch with the computed items sum recorded.
3. **Given** products 135–144, whose descriptions contradict their names/specs, **When** loaded, **Then** the name and specs are authoritative and the description is marked untrusted (not to be shown to customers).
4. **Given** product 96 (two inactive promotions, 18% and 40%, and stock 0), **When** loaded, **Then** it has no effective promotion and is unavailable.
5. **Given** the real promotions, **When** effective promotions are resolved, **Then** exactly four products have one: 90 (18%), 94 (8%), 121 (20%) and 127 (10%). **Given** a fixture with two active promotions on one product, **Then** the largest applies.
6. **Given** products 113 and 136 (`discontinued`, 136 with 13 units), **When** loaded, **Then** both are not sellable regardless of stock.
7. **Given** product 130 (`coming_soon`, referenced by orders 3 and 14), **When** loaded, **Then** it is marked "coming soon" and not sellable, and the order references are kept and flagged.
8. **Given** customer text in different Unicode forms (a fixture with "Ponta Porã" both decomposed and composed), **When** loaded, **Then** all text is stored in NFC and both values compare equal. **Given** a CRLF file whose last row has no trailing newline, **Then** no value carries a trailing `\r`.
9. **Given** customers 11 and 43 sharing `bruno.martins@jmail.com`, **When** loaded, **Then** both customers are kept and the shared email is flagged.
10. **Given** order 1 (with tracking code and delivery date) and order 9 (both empty), **When** loaded, **Then** order 1 keeps its values and order 9 stores NULL for both.
11. **Given** a database already seeded, **When** the seed runs again, **Then** row counts and per-table checksums are identical to the first run.

---

### User Story 2 - Data quality report (Priority: P1) · PR A

Each seed regenerates a human-readable report listing every anomaly found, the rule applied,
the affected record IDs and counts per anomaly type, traceable to DL-001.

**Why this priority**: handling the deliberate inconsistencies explicitly is part of the
evaluation (constitution principle III); the report is the evidence.

**Independent Test**: render the report from the dataset (no database needed) and compare it
with the committed `docs/data-quality-report.md`.

**Acceptance Scenarios**:

1. **Given** the challenge dataset, **When** the report is rendered, **Then** it lists each anomaly type with its description, rule, affected IDs and count, and every DL-001 finding maps to an anomaly type or to "enforced by validation".
2. **Given** an unchanged dataset, **When** the report is rendered in CI, **Then** it is byte-identical to the committed report.
3. **Given** a row that fails schema validation, **When** the seed runs, **Then** it fails with a message naming the file, row and field, and the database is unchanged.

---

### User Story 3 - Search the policy manual (Priority: P1) · PR B

Agent tools search the store policy manual and get back the relevant section(s), each with its
section number, title and parent breadcrumb, so answers can cite "§4 > 4.1".

**Why this priority**: policy questions (returns, shipping, warranty, payment) are a core part of
the challenge; retrieval quality drives answer quality.

**Independent Test**: index the manual with the deterministic fake embedder; run fixed queries
and check the top results.

**Acceptance Scenarios**:

1. **Given** the indexed manual and the deterministic fake embedder, **When** searching "posso devolver meu pedido?", **Then** §4.1 (Direito de Arrependimento) is in the top 3 of the combined ranking **and** in the top 3 of the vector ranking alone.
2. **Given** the real embeddings provider (opt-in test run), **When** searching English and Spanish variants of the same question, **Then** §4.1 is in the top 3 results.
3. **Given** the embeddings provider is unavailable or errors, **When** searching, **Then** results are still returned using full-text search only, and the degradation is logged.
4. **Given** a multi-word question where not every word appears in one section, **When** searching full-text only, **Then** sections matching any of the words are still returned.
5. **Given** the same query is searched twice, **When** the second search runs, **Then** its embedding is served from the cache without calling the provider.

---

### User Story 4 - Search and recommend products (Priority: P2) · PR B

Agent tools search products by meaning and keywords ("violão para iniciante com captação"),
filter the results, and find products similar to a given one ("we don't have X, but here are
similar ones").

**Why this priority**: needed by the product and recommendation tools in #6.

**Independent Test**: index products with the fake embedder; check that untrusted descriptions are
absent from indexed text, that a name query returns the product, that filters apply and that
similar-product search makes no provider call.

**Acceptance Scenarios**:

1. **Given** products 135–144, **When** the catalog index is built, **Then** no description text from those products appears in indexed text.
2. **Given** product "Yamaha C40 Nylon Natural", **When** searching "Yamaha C40", **Then** it is the top result.
3. **Given** filters (category, only sellable, maximum price, excluded IDs), **When** searching, **Then** every hit satisfies them.
4. **Given** product 96 (out of stock), **When** asking for products similar to it that are sellable and in the same category, **Then** the results exclude 96 and every non-sellable product, and no embeddings provider call is made.

---

### User Story 5 - Seed any environment safely (Priority: P2) · PR A (safety) + PR B (production run)

The same seed command targets the local database or the production database. It shows the
target and requires explicit confirmation for anything that is not local.

**Why this priority**: required to deploy, and the seed drops tables, so a mistaken target must
be hard to hit.

**Independent Test**: run the seed against a non-local URL without confirmation (refused), then
against production with confirmation (succeeds).

**Acceptance Scenarios**:

1. **Given** a non-local database URL, **When** the seed runs without `--yes`, **Then** it prints the target host and refuses.
2. **Given** `ENVIRONMENT=production` and the fake embedder configured, **When** the seed runs, **Then** it refuses.
3. **Given** the production database with `--yes` and the real embedder, **When** the seed runs, **Then** it succeeds with the same store-table row counts and checksums as locally.
4. **Given** no database URL configured, **When** the seed runs, **Then** it fails fast with a clear message.

### Edge Cases

- Policy text contains contradictions (two WhatsApp numbers in §1.2 vs §7; installment table vs §3.1; email with and without accent): the manual is indexed as written; the three known conflicts are recorded as static anomalies with the authoritative value per DL-002 (§1.2 contact, unaccented email, §3.1 installments).
- Product `specs` JSON has different keys per category (4 schemas): each category's schema is validated; unknown or missing keys fail validation.
- Duplicate promotions per product (93, 96, 99): all rows kept; resolution picks the effective one. Promotions have no validity dates: `is_active` is the only source of truth.
- An order item references a non-sellable product (130 in orders 3 and 14): kept and flagged, never dropped.
- Empty CSV cells: NULL for nullable columns (tracking code, estimated delivery, notes), a validation error for required ones.
- Embeddings provider rate limit (free tier: 3 requests and 10K tokens per minute) during seeding: requests are batched by token budget and `Retry-After` is honoured; if it still fails, the seed aborts with the database unchanged.
- Another feature's table has a foreign key to an owned table: the seed fails rather than touching that table.
- Two seeds started at the same time: the second waits for the first (lock) and then runs on its own.
- The source CSVs use CRLF line endings and the last row has no trailing newline: parsed values never carry a trailing `\r`, and the last row is read like any other. Git never rewrites the bytes of the challenge files.

## Requirements *(mandatory)*

### Functional Requirements

**Ingestion and validation**

- **FR-001**: The system MUST read the challenge CSVs and policy PDF from `challenge/` without modifying them, and the repository MUST keep their bytes unchanged (no line-ending conversion).
- **FR-002**: The system MUST validate every row against a typed schema (types, required fields, allowed status/payment values, per-category specs keys, referential integrity between orders, items, customers, products, categories and promotions) before loading anything. Empty cells MUST become NULL for nullable columns and MUST be a validation error for required ones.
- **FR-003**: On any validation or configuration error the system MUST exit with a non-zero code and a message naming the file, row and field (or the setting), leaving the target database unchanged.
- **FR-004**: The system MUST normalize all text fields to Unicode NFC before storing, comparing or indexing, and CSV parsing MUST NOT leave line-ending characters in values.

**Correction rules** (each one an explicit, separately tested rule, per DL-002)

- **FR-005**: Order total mismatch: keep the original `total_brl`; record the computed items sum (current product prices × quantity, since items have no unit price) and flag the order.
- **FR-006**: Name vs description: name is authoritative; descriptions of products 135–144 are marked untrusted and excluded from customer-facing text and from search indexing.
- **FR-007**: Specs vs description: specs are authoritative.
- **FR-008**: Promotions: only active promotions apply; when several are active for one product, the largest discount is the effective one. The system MUST expose the effective promotion and the resulting promotional price per product through one shared helper and stored columns, so tools never recompute it.
- **FR-009**: Sellability: `discontinued` is never sellable; `active` with stock 0 is unavailable; `coming_soon` is shown as coming soon and not sellable. The system MUST expose a derived availability per product.
- **FR-010**: Customers sharing an email are kept and flagged.
- **FR-011**: The three known policy conflicts (contact numbers, email spelling, installment table) and the missing purchase channel on orders (the withdrawal right applies only to online purchases) MUST be recorded as anomalies with the authoritative value per DL-002.

**Report**

- **FR-012**: The seed MUST regenerate `docs/data-quality-report.md` with, per anomaly type: description, rule applied, affected IDs, count. Output MUST be deterministic and renderable without a database; CI MUST fail when the committed report differs from a fresh render.

**Retrieval index**

- **FR-013**: The policy manual MUST be split into one chunk per numbered section (subsections such as 4.1 are their own chunks), each with section number, title, parent section and parent title.
- **FR-014**: Products MUST be indexed with name, category and specs, plus description only when trusted.
- **FR-015**: Both indexes MUST support Portuguese full-text search (matching any query term, not all of them) and vector similarity search, combined into one hybrid ranking.
- **FR-016**: Embeddings MUST be produced through a provider interface with a real implementation and a deterministic fake (no network, same input → same vector); the provider is selected by configuration.
- **FR-017**: Query embeddings MUST be cached in a database table keyed by provider, model and normalized query text (NFC, casefolded, whitespace collapsed and trimmed), so the cache survives cold starts and is shared across instances. Seeding MUST NOT clear this cache.
- **FR-018**: If the embeddings provider fails at query time, search MUST fall back to full-text only and log the degradation.
- **FR-019**: Re-seeding MUST NOT re-embed unchanged documents (documents keyed by their exact NFC text; only queries use the normalized key).
- **FR-024**: Product search MUST accept filters (category, only sellable, maximum promotional price, excluded IDs) and return category and availability with each hit.
- **FR-025**: The system MUST find products similar to a given product using its stored embedding, with the same filters, excluding the product itself and without calling the embeddings provider.
- **FR-026**: Retrieval MUST reuse database connections across requests in the same serverless instance, and MUST NOT read index metadata from the database on every query.

**Operation**

- **FR-020**: A single seed command MUST build schema, load data, build indexes and write the report. In one transaction, under a database lock, it MUST drop and recreate only the tables it owns (never with `CASCADE`) and MUST NOT touch any other table.
- **FR-021**: The seed MUST be idempotent: two runs produce the same row counts and the same per-table checksums.
- **FR-022**: Secrets (database URLs, embeddings API key) MUST come only from environment variables. The seed MUST use the direct (unpooled) database URL when one is configured.
- **FR-023**: Embeddings for seeding MUST be computed before the write transaction, batched within the provider's per-minute token budget, honouring `Retry-After`. On failure the seed MUST abort with the database unchanged and MUST NOT substitute the fake embedder.
- **FR-027**: The seed MUST print the target host and database and MUST refuse non-local targets without an explicit `--yes`. It MUST refuse the fake embedder when `ENVIRONMENT=production`.
- **FR-028**: Integration tests that drop tables MUST skip on non-local database hosts unless explicitly allowed.

### Key Entities

- **Category**: product family (9); name and description.
- **Product**: ID, name, category, price, stock, status, category-specific specs, description, description-trusted flag, derived availability, effective promotion, promotional price.
- **Promotion**: product, discount percent, label, active flag; several per product possible; no validity dates.
- **Customer**: ID, name, phone, email, city (NFC); shared-email flag.
- **Order**: ID, customer, date, status, payment method, original total, computed items sum, mismatch flag, tracking code (nullable), estimated delivery (nullable), notes (nullable).
- **Order item**: order, product, quantity; flagged when the product is not sellable.
- **Policy chunk**: section number, title, parent section and title, text, full-text vector, embedding.
- **Product search document**: product, indexed text, full-text vector, embedding.
- **Data anomaly**: type, rule, affected record IDs, count. Built in memory by the ETL and rendered into the report.
- **Embedding cache entry**: provider, model, input type, text key, vector.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh environment is fully seeded (data + indexes + report) with one command in under 30 seconds with the fake embedder, and in under 3 minutes with the real provider on its free-tier rate limits.
- **SC-002**: Every DL-001 finding is traceable to an anomaly type in the report or to a validation rule; every correction rule has at least one dedicated test.
- **SC-003**: Two consecutive seeds produce identical row counts and table checksums, and the committed report matches a fresh render.
- **SC-004**: "posso devolver meu pedido?" returns §4.1 in the top 3 with the fake embedder (in CI, also in the vector ranking alone), and EN/ES variants do the same with the real provider.
- **SC-005**: With the embeddings provider down, policy search still returns results (full-text) for 100% of the reference queries (a fixed set of 5 questions covering returns, shipping, installments, warranty and contact).
- **SC-006**: Zero description text from products 135–144 appears in indexed text.
- **SC-007**: The seed succeeds against the production database with the same store-table checksums as locally, and leaves tables owned by other features unchanged.

## Assumptions

- The database and backend scaffolding come from #3; this feature adds data and indexes on top.
- Seeding is a full rebuild of the owned tables (data set is tiny: under 200 rows); document embeddings are reused through the cache.
- Product 130 appearing in orders is historical data and is preserved; it is flagged, not corrected.
- `items_total_brl` uses current product prices because order items have no unit price; it is evidence for the mismatch flag, not a historical price.
- The real clock is used elsewhere; this feature does not compute dates or eligibility.
- Payment-method pricing (PIX discount, installments) belongs to the agent epic; this feature provides the promotional price it starts from.
- The manual is in Portuguese; cross-language retrieval relies on the multilingual real embeddings provider (the fake embedder only guarantees the Portuguese CI case).
- Voyage without a payment method is limited to 3 requests and 10K tokens per minute. Production needs a payment method on the account (the free token allowance still applies); the README says so.
