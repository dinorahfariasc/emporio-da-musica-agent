# Data Model: Data Foundation

Postgres 16 + `vector` + `unaccent` extensions. All tables live in `public`. **Owned by this
feature**: every table below.

- The seed **drops and recreates** all of them in one transaction, never with `CASCADE`, except
  `embedding_cache`, which is created if missing and persists (research R7, R10). If a table
  from another feature has a foreign key to an owned table, the seed fails instead of touching it.
- All text is NFC. Empty CSV cells become NULL in nullable columns and are validation errors in
  required ones.

**PR A** creates the store tables. **PR B** adds the retrieval tables.

## Store tables (PR A)

### categories
| Column | Type | Notes |
|---|---|---|
| category_id | int PK | |
| name | text not null | |
| description | text not null | |

### products
| Column | Type | Notes |
|---|---|---|
| product_id | int PK | |
| category_id | int FK → categories | |
| name | text not null | authoritative (FR-006) |
| price_brl | numeric(10,2) not null | > 0 |
| stock_quantity | int not null | ≥ 0 |
| status | text not null | `active` \| `discontinued` \| `coming_soon` (CHECK) |
| specs | jsonb not null | authoritative over description (FR-007); schema per category, see below |
| description | text not null | original text, kept for audit |
| description_trusted | bool not null | false for 135–144 (FR-006) |
| availability | text not null | derived: `in_stock` \| `out_of_stock` \| `discontinued` \| `coming_soon` (FR-009) |
| is_sellable | bool not null | derived: `availability = 'in_stock'` |
| effective_promotion_id | int null FK → promotions | derived (FR-008) |
| effective_discount_percent | int not null default 0 | derived (FR-008) |
| promo_price_brl | numeric(10,2) not null | derived: `promo_price(price_brl, effective_discount_percent)`, ROUND_HALF_UP; equals `price_brl` when there is no promotion |
| created_at | date not null | |

**Availability rule** (`app/catalog/rules.py::availability`):
- `discontinued` → `discontinued`, whatever the stock (113, 136);
- `coming_soon` → `coming_soon` (130);
- `active` and stock = 0 → `out_of_stock` (96);
- otherwise `in_stock` (values match `Availability` in `app/chat/protocol.py`, chat contract #4).

**Effective promotion** (`effective_promotion`): among `is_active` promotions for the product,
the largest `discount_percent`; ties are broken by the lowest `promotion_id`. None → null / 0.

On the real data, exactly 4 products have one: **90 → 18%, 94 → 8%, 121 → 20%, 127 → 10%**.
"Max wins" is exercised only by the `promotions_multi_active.csv` fixture, because every
duplicate in the real data is inactive.

**Specs schemas** (validated per category; extra or missing keys are an error):
| Categories | Keys |
|---|---|
| 1 Guitarras, 2 Baixos | body, neck, strings, color |
| 3 Baterias | shells, pieces, hardware, color |
| 4 Teclados | keys, type, polyphony, color |
| 5 Violões, 9 Ukuleles | top, back_sides, neck, strings, scale, electronics, color |
| 6, 7, 8 | no products; no schema (a product there fails validation until one is defined) |

### promotions
| Column | Type | Notes |
|---|---|---|
| promotion_id | int PK | |
| product_id | int FK → products | several rows per product allowed |
| discount_percent | int not null | 1–100 |
| description | text not null | label, e.g. "Black Friday" |
| is_active | bool not null | the only validity signal (no dates in the source) |

### customers
| Column | Type | Notes |
|---|---|---|
| customer_id | int PK | |
| name | text not null | |
| phone | text not null | as given; `^\(\d{2}\) \d{4,5}-\d{4}$` |
| phone_digits | text not null | digits only, for identity matching (#6) |
| email | text not null | stored lowercased; **not unique** (customers 11 and 43) |
| email_shared | bool not null | FR-010 |
| city | text not null | NFC |

### orders
| Column | Type | Notes |
|---|---|---|
| order_id | int PK | |
| customer_id | int FK → customers | |
| order_date | date not null | |
| status | text not null | `pending` \| `confirmed` \| `shipped` \| `delivered` \| `cancelled` |
| payment_method | text not null | `pix` \| `boleto` \| `debit` \| `credit_3x` \| `credit_6x` \| `credit_12x` |
| total_brl | numeric(10,2) not null | **original amount paid, never corrected** (FR-005) |
| items_total_brl | numeric(10,2) not null | Σ quantity × **current** `price_brl` (items carry no unit price); evidence for the mismatch flag only |
| total_mismatch | bool not null | `total_brl <> items_total_brl` (orders 3, 20) |
| tracking_code | text **null** | empty in orders 9–20 → NULL |
| estimated_delivery | date **null** | empty in orders 9–20 → NULL |
| notes | text **null** | empty except orders 17–20 → NULL |

### order_items
| Column | Type | Notes |
|---|---|---|
| order_id | int FK → orders | PK (order_id, product_id) |
| product_id | int FK → products | |
| quantity | int not null | > 0 |
| product_not_sellable | bool not null | product status is not `active`: discontinued or coming soon (130 in orders 3, 14). A stock-out does not count (96 in order 4 is not flagged) |

## Retrieval tables (PR B)

### policy_chunks
| Column | Type | Notes |
|---|---|---|
| section | text PK | `"4.1"`, `"4"` (intro), `"2"` |
| parent_section | text null | `"4"` for `"4.1"` |
| parent_title | text null | `"Política de Trocas e Devoluções"` |
| title | text not null | `"Direito de Arrependimento (Compras Online)"` |
| body | text not null | cleaned section text |
| search_text | text not null | breadcrumb + body |
| tsv | tsvector generated | `to_tsvector('pt_unaccent', search_text)`, GIN |
| embedding | vector(768) not null | |
| ordinal | int not null | document order |

### product_search_docs
| Column | Type | Notes |
|---|---|---|
| product_id | int PK FK → products | |
| search_text | text not null | name + category name + specs (`key: value`, sorted) + description **only if trusted** |
| tsv | tsvector generated | GIN |
| embedding | vector(768) not null | also used by `similar_to_product` (no provider call) |

All 65 products are indexed. Availability and price filters join `products`, so "we have it but
it's discontinued" stays answerable.

### embedding_cache (persistent, created if missing, never dropped by the seed)
| Column | Type | Notes |
|---|---|---|
| provider | text | `gemini` \| `fake` |
| model | text | `gemini-embedding-001` \| `fake-ngram-v1` |
| input_type | text | `document` \| `query` |
| text_key | text | documents: sha256 of exact NFC text; queries: sha256 of `normalize_for_cache` |
| embedding | vector(768) not null | |
| created_at | timestamptz default now() | |
| | | **PK (provider, model, input_type, text_key)** |

### index_metadata (single row)
| Column | Type | Notes |
|---|---|---|
| id | bool PK default true, CHECK (id) | singleton |
| provider | text not null | provider used to build the indexes |
| model | text not null | |

Search compares the configured provider and model with this row (cached in-process for 5
minutes). On a mismatch it runs full-text only and logs a warning.

## Anomalies (in memory, rendered into the report)

`Anomaly(type, entity, record_ids, detail, rule)`. **Count = number of affected records.**

| type | entity | count | records | rule |
|---|---|---|---|---|
| order_total_mismatch | order | 2 | 3, 20 | keep original total; flag |
| untrusted_description | product | 10 | 135–144 | name/specs win; description hidden and not indexed |
| out_of_stock_active | product | 1 | 96 | unavailable; suggest alternatives |
| discontinued | product | 2 | 113, 136 | not sellable; 136 has stock 13 |
| coming_soon | product | 1 | 130 | not sellable; shown as coming soon |
| non_sellable_in_order | order | 2 | 3, 14 (product 130) | kept; flagged |
| duplicate_promotions | product | 3 | 93, 96, 99 | only active apply; max wins |
| active_promotions | product | 4 | 90, 94, 121, 127 | informational: the only effective promotions |
| no_promotion_validity_dates | promotion | 25 | all | `is_active` is the only source of truth; no date logic |
| shared_email | customer | 2 | 11, 43 | both kept; flagged; identity checks use order number + email/phone |
| missing_purchase_channel | order | 20 | all | §4.1 withdrawal right needs the channel; #6 asks the customer |
| nfc_normalized | customer/any | 0 | none | normalize to NFC (DL-001 corrected in DL-005: CRLF, not two encodings) |
| empty_category | category | 3 | 6, 7, 8 | informational; agent says not available |
| policy_conflict | policy | 3 | `1.2-vs-7-whatsapp`, `1.2-email-accent`, `3-vs-3.1-installments` | static records: §1.2 number (67) 3341-4444; unaccented email; §3.1 wins |

## DL-001 traceability

| DL-001 finding | Handled by |
|---|---|
| 135–144 name contradicts description | `untrusted_description` |
| 135–144 specs contradict description (5 vs 4 strings, 88 vs 61 keys) | `untrusted_description` (specs win) |
| `specs` JSON schema varies by category | enforced by validation (per-category schema) |
| 96 active with zero stock | `out_of_stock_active` |
| 113 discontinued | `discontinued` |
| 136 discontinued with 13 units | `discontinued` |
| 130 coming_soon yet present in orders | `coming_soon` + `non_sellable_in_order` |
| Duplicate promotions per product (96: 18% and 40%) | `duplicate_promotions` |
| Only 4 promotions active | `active_promotions` |
| Promotions have no validity dates | `no_promotion_validity_dates` |
| Order totals differ from item sums (3, 20) | `order_total_mismatch` |
| "Ponta Porã" in two encodings | `nfc_normalized` (0: CRLF artefact; CRLF parsing enforced by validation and tested) |
| Customers 11 and 43 share an email | `shared_email` |
| Two WhatsApp numbers (§1.2 vs §7) | `policy_conflict` |
| Email with and without accent | `policy_conflict` |
| Installment table contradicts §3.1 | `policy_conflict` |
| 7-day withdrawal only online; orders lack the channel | `missing_purchase_channel` |
| *(new)* Categories 6–8 have no products | `empty_category` |
| *(new)* Empty optional order fields (9–20) | enforced by validation (`''` → NULL) |

## Relationships

```text
categories 1─* products 1─* promotions
customers 1─* orders 1─* order_items *─1 products
products 1─1 product_search_docs
policy_chunks (standalone)   embedding_cache (standalone)   index_metadata (singleton)
```
