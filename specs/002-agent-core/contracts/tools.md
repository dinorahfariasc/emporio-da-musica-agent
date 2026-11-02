# Contract: Store tools (Python, in-process; also exposed over MCP in #8)

All tools are `async def` functions in `backend/app/tools/`. The rules below apply to every tool:

- **Context**: each tool takes `ctx: ToolContext` (pool, embedder, conversation id, clock) as its
  first argument. The context is not visible to the model or to MCP.
- **Facts**: they are computed only in Python (constitution I). The model never receives raw
  rows with personal data.
- **Errors**: a tool raises `ToolError(code)` with one of these stable codes: `not_found`,
  `verification_failed`, `locked`, `not_verified`, `not_eligible`, `unavailable`, `invalid_input`.
  The adapter maps it to `tool-output-error`.
- **Products**: tools that return products also write one `data-products` part (`ProductCard[]`),
  at most 6 cards.

## Read tools (US1–US4)

| Tool | Inputs | Output (to the model) | Notes |
|---|---|---|---|
| `search_products` | `query: str`, `category_id?: int`, `max_price_brl?: Decimal`, `only_sellable: bool = True`, `limit: int ≤ 10` | `ProductView[]` + `count` | Hybrid search (001). The budget is compared with the current price (`promo_price_brl`). |
| `get_product` | `product_id?: int` or `name?: str`, `quantity?: int ≥ 1` | `ProductView` (with `stock_quantity`) or `candidates[]` (name ambiguity); with `quantity`, also `requested_quantity` and `enough_stock` | Name matching through `search_products` (limit 5). Several close candidates are returned as a list (edge case). `enough_stock = is_sellable and stock_quantity >= quantity`, computed in Python. |
| `find_similar_products` | `product_id?: int`, `description?: str`, `max_price_brl?`, `limit ≤ 5` | `ProductView[]` (sellable only, same category when `product_id` is given) | With `product_id`: `similar_to_product`. With text: `search_products`. Never offers non-sellable products (FR-011). |
| `get_active_promotions` | `category_id?` | `ProductView[]` with an active promotion | Only `is_active` promotions, through `effective_promotion`. |
| `calculate_payment_options` | `product_id?: int` or `amount_brl?: Decimal` | `PaymentOptions` | R8 rules. |
| `get_order_status` | `order_id: int`, `contact: str` | `OrderStatusView` | Uses the `conversation_state` verification (data-model). Errors: `verification_failed` (one generic error for a wrong contact and for an unknown order), `locked`. An order already verified in this conversation does not need the contact again. |
| `search_policies` | `query: str`, `limit ≤ 5` | `[{section, breadcrumb, body}]` | Hybrid search. The body is marked as reference text. |
| `get_store_info` | none | `StoreInfo` | Clock + §1/§2 constants + holidays. |

## Action tools (US6, #7)

These tools act only on the customer's explicit request (FR-020). The system prompt requires an
explicit request, and the tool demands `confirmed_by_customer: bool = True` in its input as a
second guard.

| Tool | Inputs | Output |
|---|---|---|
| `check_return_eligibility` | `order_id`, `reason: regret\|defect\|preference`, `bought_online?: bool` | `Eligibility` (the order must be verified) |
| `request_return` | `order_id`, `reason`, `details: str`, `confirmed_by_customer`, `bought_online?: bool` (needed for regret) | `{request_id, type, next_step}`. Refused unless `check_return_eligibility` is `eligible`; the check runs again inside the tool. |
| `register_complaint` | `summary: str`, `order_id?`, `confirmed_by_customer` | `{request_id, response_within: "24 business hours"}` |
| `handoff_to_human` | `reason: str`, `confirmed_by_customer` | `{request_id, channel, hours}` |

## MCP exposure (US7, #8)

- **Tools**: the same functions are registered with FastMCP. `ctx` is built by the MCP layer per
  call. The MCP conversation id is `mcp:<client_id>`, so verification state is separate per
  client.
- **Auth**: `Authorization: Bearer <MCP_API_KEY>`. A missing or invalid key gets 401.
- **Business logic**: none in the MCP layer (constitution VI).
