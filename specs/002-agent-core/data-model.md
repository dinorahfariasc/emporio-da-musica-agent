# Data Model: Agent core (002)

Store data (`products`, `promotions`, `customers`, `orders`, `order_items`, `policy_chunks`) is
owned by 001 and read-only here. This feature adds the tables and in-memory types below.

## New tables (`backend/app/agent/schema.sql`, applied by the seed and tests)

### `conversation_state`

The server-side security state for one conversation (FR-015, FR-016, R6).

| Column | Type | Rules |
|---|---|---|
| `conversation_id` | text PK | the chat contract `id`; at most 128 chars, pattern `[A-Za-z0-9_-]+` |
| `verified_order_ids` | int[] NOT NULL DEFAULT '{}' | orders verified in this conversation; verification is **per order** |
| `failed_attempts` | int NOT NULL DEFAULT 0 | incremented atomically on each failed verification |
| `locked` | boolean NOT NULL DEFAULT false | set when `failed_attempts` reaches 3; no more verification in this conversation |
| `updated_at` | timestamptz NOT NULL DEFAULT now() | rows older than 7 days may be purged |

**State transitions**

| From | Event | To |
|---|---|---|
| no row | first verification attempt | row inserted (`INSERT … ON CONFLICT DO NOTHING`) |
| unlocked | success | `verified_order_ids += order_id` |
| unlocked | failure | `failed_attempts += 1`; at 3, `locked = true` (one `UPDATE … RETURNING`) |
| locked | any attempt | refused without checking data; human support offered |

### `service_requests` (P2, #7)

Records created only after an explicit customer request (FR-020).

| Column | Type | Rules |
|---|---|---|
| `request_id` | bigint identity PK | |
| `conversation_id` | text NOT NULL | |
| `type` | text | `return` \| `exchange_defect` \| `exchange_preference` \| `complaint` \| `handoff` |
| `order_id` | int NULL REFERENCES orders | required for return/exchange; the order must be verified in this conversation |
| `reason` | text NOT NULL | the customer's words, truncated to 1000 chars; personal data masked |
| `eligibility` | jsonb NULL | the decision record for return/exchange (rule, window, dates) |
| `status` | text NOT NULL DEFAULT 'open' | |
| `created_at` | timestamptz NOT NULL DEFAULT now() | |

## Domain types (Pydantic, in `app/agent/` and `app/tools/`)

### Intent and Route (FR-001, FR-002)

`Intent` (`Literal`) is one of:

- `product_search`
- `product_details`
- `promotions`
- `payment_options`
- `order_status`
- `policy_question`
- `store_info`
- `service_request`
- `greeting`
- `out_of_scope`
- `multi_intent`
- `unclear`

`Route = {intent: Intent, confidence: float 0..1, router: "jev" | "haiku" | "fake",
path: "specialist" | "general", model: str}`.

Choosing the path:

- **`specialist`**: when all of these hold:
  - `confidence ≥ ROUTER_CONFIDENCE_THRESHOLD`;
  - the intent is not `multi_intent` or `unclear`;
  - the intent has a specialist.
- **`general`**: otherwise.
- **`greeting` and `out_of_scope`**: these use the specialist model with **no tools**.

`route` in the contract metadata maps to `{intent, confidence, router}`.

### Specialist tool sets

| Intent | Tools |
|---|---|
| `product_search` | `search_products`, `find_similar_products` |
| `product_details` | `get_product`, `find_similar_products`, `calculate_payment_options` |
| `promotions` | `get_active_promotions` |
| `payment_options` | `get_product`, `calculate_payment_options`, `search_policies` |
| `order_status` | `get_order_status` |
| `policy_question` | `search_policies` |
| `store_info` | `get_store_info`, `search_policies` |
| `service_request` (#7) | `get_order_status`, `check_return_eligibility`, `request_return`, `register_complaint`, `handoff_to_human` |

The general path gets every tool.

### ProductView (tool output, FR-005, FR-007, FR-008)

| Field | Source |
|---|---|
| `product_id`, `name`, `category` | `products` / `categories` |
| `price_brl` | `products.price_brl` |
| `promo_price_brl`, `discount_percent` | only when `effective_discount_percent > 0`, else null |
| `availability`, `is_sellable` | stored columns (001 rules) |
| `specs` | `products.specs` |
| `description` | `display_description()`; null for untrusted descriptions |

Cards use the contract `ProductCard` mapping from the 001 retrieval contract.

### PaymentOptions (FR-006)

| Field | Content |
|---|---|
| `amount_brl` | the current price |
| `pix` | `{applies, price_brl \| null, reason}` |
| `installments` | `[{count, value_brl}]`, only the allowed counts |
| `combined_payment_allowed` | true only above R$ 2.000 |

### Verification and OrderStatusView (FR-013…FR-017)

**Input**: `order_id: int` and `contact: str`. The tool decides whether `contact` is an email or a
phone:

- an email is compared after `casefold` and `strip`;
- a phone is compared on its digits only, against `customers.phone_digits` of **that order's
  customer**.

**Outcomes** (`VerificationResult`):

| Outcome | Data returned |
|---|---|
| `verified` | the order view |
| `failed` | none; the same generic message whether the order exists or not |
| `locked` | none |

**`OrderStatusView` fields**:

- `order_id`, `status`, `order_date`;
- `items` (name and quantity);
- `total_brl`, `tracking_code`, `estimated_delivery`;
- `delivery_overdue` (true when `shipped` and `estimated_delivery < today`);
- `cancellation_reason`: the order `notes` when cancelled.

There is never an email or phone in any output.

### StoreInfo (FR-018)

| Field | Content |
|---|---|
| `now_local` | in America/Campo_Grande |
| `is_open_now` | |
| `today_hours` | |
| `next_opening` | |
| `holiday_name` | |
| `address`, `phone`, `whatsapp`, `email` | the official values (§1.2 resolution) |

### Eligibility (P2, #7, FR-019)

**Input**:

| Field | Values |
|---|---|
| `order_id` | must be verified in this conversation |
| `reason` | `regret` \| `defect` \| `preference` |
| `bought_online` | `bool \| None`; must be asked when `None` and the reason is `regret` |
| `today` | from the `Clock` |

**Output**: `{eligible, rule: "4.1" | "4.2" | "4.3" | "4.4" | "8.1", window_days, deadline,
reason_code, next_step}`.

**Reference date**:

- delivery date = `estimated_delivery`, an assumption documented in the spec;
- purchase date = `order_date`.

### Turn log (FR-026, FR-024)

One structured JSON log line per turn, with these fields:

- `conversation_id` (hashed)
- `intent`, `confidence`, `router`, `path`, `model`
- `tools` (names and outcome codes)
- `input_tokens`, `output_tokens`
- `latency_ms`, `first_token_ms`
- `error_code`

Emails and phones in any logged text are masked by `mask_pii()`.
