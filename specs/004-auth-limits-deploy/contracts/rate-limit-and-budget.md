# Contract: Rate limit and daily budget responses

Both checks run inside `POST /api/chat`, after `require_service_account` succeeds and before the
agent graph is invoked. Order: rate limit first (cheaper, catches the common "double click /
runaway loop" case), then daily budget.

## Rate limit (FR-010, FR-013, FR-014)

- Limit: 20 requests per rolling-minute window per account (fixed window, see `research.md` R5).
- On the 21st+ request within the same UTC minute bucket:
  - `429 Too Many Requests`
  - `Retry-After: <seconds until the next minute boundary>` header
  - Body — the existing `#4` contract shape, fixture `http-429-rate-limited.json`
    (`docs/contracts/chat-stream.md`), not a new shape invented by this feature:
    ```json
    { "error": { "code": "rate_limited", "message": "Muitas mensagens em pouco tempo. Aguarde alguns segundos e tente de novo.", "retryAfterSeconds": 30 } }
    ```
    `message` is already localized server-side (pt-BR by default, per the fixture); this feature
    does not add a new localization mechanism, it reuses whatever the chat endpoint already does
    for user-facing copy.
- A turn already streaming when the limit is reached elsewhere is unaffected (the check only runs
  at the start of a new request, never mid-stream).

## Daily token budget (FR-011, FR-012, FR-013)

- Budget: 200,000 combined input+output tokens per account per local day
  (`America/Campo_Grande`, reset at local midnight).
- If the account's `token_usage_daily` row for today already has `tokens_used >= 200000`:
  - `429 Too Many Requests`
  - Body — again the `#4` contract shape, fixture `http-429-budget-exhausted.json`:
    ```json
    { "error": { "code": "budget_exhausted", "message": "Você atingiu o limite diário de uso. Volta a funcionar à meia-noite.", "retryAfterSeconds": 86399 } }
    ```
  - `retryAfterSeconds` is computed from "now" to the next `America/Campo_Grande` midnight, so a
    client can show a countdown without re-implementing the timezone rule itself.

## After the turn finishes

- The handler reads the actual prompt+completion token counts already produced by the agent run
  (same numbers the router/model telemetry logs today, per constitution II) and adds them to
  `token_usage_daily` for the account's current day — a single upsert, not per streamed chunk.
- If the turn errors before any model call happened, nothing is added (no spend occurred).
- If the stream is dropped by the client mid-answer, whatever tokens the provider already reports
  as consumed up to that point are recorded (same as a completed turn) — a partial answer still
  costs real provider tokens.

## Independent of each other

A request that is only over the per-minute limit (but has daily budget left) gets `rate_limited`;
a request that is only over budget (but within the per-minute limit) gets `budget_exhausted`; a
request over both gets `rate_limited` (checked first, cheaper, and the more common failure mode).

## Deliberate choices (QA review #44)

- **An empty-message request (the canned greeting, no model call) still counts against the
  per-minute rate limit.** The rate-limit check runs before the handler knows whether the message
  is empty, by design: the limit exists to cap request *volume* against the service (including a
  scripted/buggy client hammering the endpoint with empty bodies), not only paid model calls — the
  daily token *budget*, separately, is never touched by an empty-message request since no model
  runs. A request refused by the rate limit or the budget check itself also consumes no budget
  (`check_budget` is a pure read; only `record_usage`, reached after a turn actually runs, writes).
- **The budget is soft under concurrency, by design.** Two requests for the same account arriving
  at nearly the same instant can both pass `check_budget` (each sees the pre-turn balance) before
  either calls `record_usage`, so the account can briefly go slightly over 200,000 tokens for that
  day before the *next* request is refused. Making this strictly atomic would mean reserving an
  estimated token cost before the model call (an estimate, since the real cost is unknown until the
  provider responds) and reconciling afterward — real complexity for a one-evaluator-scale
  deployment where the realistic failure mode is one client sending turns sequentially, not a
  deliberate concurrent-request attack on the budget specifically (the per-minute rate limit above
  already bounds how much damage a burst can do either way).
