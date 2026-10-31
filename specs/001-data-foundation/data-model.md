# Data Model: Data Foundation

Postgres 16 + `vector` + `unaccent` extensions. All tables live in `public`. **Owned by this
feature**: every table below. The seed truncates and reloads all of them except `embedding_cache`,
which persists (clarifications 2 and 4). Truncation never uses `CASCADE`: if a table from another
feature has a foreign key to an owned table, the seed fails instead of emptying it. All text is NFC.

## Store tables

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
| availability | text not null | derived: `available` \| `out_of_stock` \| `discontinued` \| `coming_soon` (FR-009) |
| is_sellable | bool not null | derived: `availability = 'available'` |
| effective_promotion_id | int null FK → promotions | derived (FR-008) |
| effective_discount_percent | int not null default 0 | derived (FR-008) |
| created_at | date not null | |

**Availability rule** (`app/catalog/rules.py::availability`):
- `discontinued` → `discontinued`, whatever the stock (113, 136);
- `coming_soon` → `coming_soon` (130);
- `active` and stock = 0 → `out_of_stock` (96);
- otherwise `available`.

**Effective promotion** (`effective_promotion`): among `is_active` promotions for the product,
the largest `discount_percent`; ties are broken by the lowest `promotion_id`. None → null / 0.

**Specs schemas** (validated per category, extra/missing keys are an error):
| Categories | Keys |
|---|---|
| 1 Guitarras, 2 Baixos | body, neck, strings, color |
| 3 Baterias | shells, pieces, hardware, color |
| 4 Teclados | keys, type, polyphony, color |
| 5 Violões, 9 Ukuleles | top, back_sides, neck, strings, scale, electronics, color |
| 6, 7, 8 | no products in the data; a schema is defined only when a product appears (unknown category schema means validation fails) |

### promotions
| Column | Type | Notes |
|---|---|---|
| promotion_id | int PK | |
| product_id | int FK → products | several rows per product allowed |
| discount_percent | int not null | 1–100 |
| description | text not null | label, e.g. "Black Friday" |
| is_active | bool not null | |

### customers
| Column | Type | Notes |
|---|---|---|
| customer_id | int PK | |
| name | text not null | |
| phone | text not null | as given, `(67) 9XXXX-XXXX` format validated |
| phone_digits | text not null | digits only, for identity matching (epic 002) |
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
| total_brl | numeric(10,2) not null | **original amount, never corrected** (FR-005) |
| items_total_brl | numeric(10,2) not null | Σ quantity × current product price |
| total_mismatch | bool not null | `total_brl <> items_total_brl` (orders 3, 20) |
| tracking_code | text null | |
| estimated_delivery | date null | |
| notes | text null | |

### order_items
| Column | Type | Notes |
|---|---|---|
| order_id | int FK → orders | PK (order_id, product_id) |
| product_id | int FK → products | |
| quantity | int not null | > 0 |
| product_not_sellable | bool not null | product is not sellable now (130 in orders 3, 14) |

## Retrieval tables

### policy_chunks
| Column | Type | Notes |
|---|---|---|
| section | text PK | `"4.1"`, `"4"` (intro), `"2"` |
| parent_section | text null | `"4"` for `"4.1"` |
| title | text not null | `"Direito de Arrependimento (Compras Online)"` |
| body | text not null | cleaned section text |
| search_text | text not null | breadcrumb + body |
| content_hash | text not null | sha256(search_text) |
| tsv | tsvector generated | `to_tsvector('pt_unaccent', search_text)`, GIN |
| embedding | vector(1024) not null | |
| ordinal | int not null | document order |

### product_search_docs
| Column | Type | Notes |
|---|---|---|
| product_id | int PK FK → products | |
| search_text | text not null | name + category + specs (`key: value`) + description **only if trusted** |
| content_hash | text not null | |
| tsv | tsvector generated | GIN |
| embedding | vector(1024) not null | |

All products are indexed, including non-sellable ones. Availability filtering is the tool's job,
so "we have it but it's discontinued" stays answerable.

### embedding_cache (persistent, not truncated)
| Column | Type | Notes |
|---|---|---|
| provider | text | `voyage` \| `fake` |
| model | text | `voyage-4` \| `fake-ngram-v1` |
| input_type | text | `document` \| `query` |
| text_hash | text | sha256 of normalized text |
| embedding | vector(1024) not null | |
| created_at | timestamptz default now() | (excluded from checksums) |
| | | **PK (provider, model, input_type, text_hash)** |

Serves both FR-017 (query cache) and FR-019 (no re-embedding of unchanged documents).

### index_metadata (single row)
| Column | Type | Notes |
|---|---|---|
| id | bool PK default true, CHECK (id) | singleton |
| provider | text not null | provider used to build the indexes |
| model | text not null | |
| dataset_fingerprint | text not null | sha256 of input files |

Search compares the configured provider/model with this row. On a mismatch, vectors are not
comparable, so search uses full-text only and logs a warning.

### data_anomalies
| Column | Type | Notes |
|---|---|---|
| anomaly_id | serial PK | assigned in deterministic order |
| type | text not null | see catalogue below |
| entity | text not null | `product` \| `order` \| `customer` \| `promotion` \| `category` \| `policy` |
| record_ids | text[] not null | sorted |
| detail | text not null | human-readable, PII-masked |
| rule | text not null | rule applied (DL-002 reference) |

### Anomaly catalogue (expected counts on the current dataset)

| type | entity | expected | rule |
|---|---|---|---|
| order_total_mismatch | order | 2 (3, 20) | keep original total; flag |
| untrusted_description | product | 10 (135–144) | name/specs win; description hidden and not indexed |
| out_of_stock_active | product | 1 (96) | unavailable; suggest alternatives |
| discontinued | product | 2 (113, 136) | not sellable; 136 has stock 13 |
| coming_soon | product | 1 (130) | not sellable; shown as coming soon |
| non_sellable_in_order | order | 2 (3, 14 → product 130) | kept; flagged |
| duplicate_promotions | promotion | 3 products (93, 96, 99) | only active apply; max wins |
| shared_email | customer | 1 group (11, 43) | both kept; flagged |
| missing_purchase_channel | order | 1 group (all 20 orders) | §4.1 withdrawal right applies only to online purchases and orders don't record the channel; eligibility tools (epic 002) must ask the customer |
| nfc_normalized | customer/any | 0 | normalize to NFC (DL-001 corrected in DL-005: CRLF, not two encodings) |
| empty_category | category | 3 (6, 7, 8) | informational; agent says not available |
| policy_conflict | policy | 3 (WhatsApp 3341-4444 in §1.2 vs 3321-4500 in §7 intro; accented email in §1.2 vs cover; installment table vs §3.1) | §1.2 number; unaccented email; §3.1 wins |

Every row type has at least one dedicated unit test. The count test fails if the dataset drifts.

## Relationships

```text
categories 1─* products 1─* promotions
customers 1─* orders 1─* order_items *─1 products
products 1─1 product_search_docs
policy_chunks (standalone)   embedding_cache (standalone, keyed by text hash)
```
