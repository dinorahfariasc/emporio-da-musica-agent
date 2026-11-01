# Contract: Service JWT (BFF → backend)

The Next.js route handler for `POST /api/chat` attaches an `Authorization: Bearer <token>` header
to every request it forwards to FastAPI's `POST /api/chat`. This replaces the current unauthenticated
proxy (`frontend/src/app/api/chat/route.ts` today forwards with no auth header — see "Auth is
added in #10" comment in that file).

## Minting (frontend, `src/lib/auth/service-jwt.ts`)

- Algorithm: **HS256**.
- Secret: `process.env.SERVICE_JWT_SECRET` (same raw string value configured on the backend's
  `SERVICE_JWT_SECRET` env var — this is a shared symmetric secret, not a key pair).
- Claims:
  - `sub`: the account's `users.id` (uuid string) from the Auth.js session.
  - `username`: the account's username (telemetry only).
  - `iat`: now.
  - `exp`: `iat + 120` seconds.
- Minted fresh for every `/api/chat` request; never cached or reused across requests.
- The backend accepts up to 30 seconds of clock skew between the two services when checking `iat`/
  `exp` (small VM clock drift is expected; rejecting on skew alone would be a false-positive
  outage, not a security win at this token lifetime).
- If `SERVICE_JWT_SECRET` is unset, the route handler MUST fail the request (500) rather than send
  an unsigned or well-known-secret token.
- Before minting, the route handler re-checks the account's `disabled_at` is still null (see
  `data-model.md` note); if disabled, respond 401 without forwarding to the backend.

## Verifying (backend, `app/auth/service_jwt.py` + `app/auth/dependency.py`)

- A FastAPI dependency `require_service_account` is added to `POST /api/chat` (and any future
  authenticated route).
- Behavior:
  | Condition | Response |
  |---|---|
  | `SERVICE_JWT_SECRET` not configured on the backend | `500` — configuration error, logged, never silently accepted (fail closed, FR-015). |
  | `Authorization` header missing or not `Bearer <token>` | `401 unauthorized` (`http-401.json` fixture) |
  | Token signature invalid | `401 unauthorized` |
  | Token expired beyond the 30s skew allowance | `401 unauthorized` |
  | Token valid | request proceeds; `AccountClaims(user_id, username)` is available to the handler both for limit checks (`app/limits/enforce.py`) and to scope conversation state to `(account, conversation_id)` per FR-009a |
- The backend never re-derives or checks a password; this dependency is the *only* authentication
  surface of `POST /api/chat`.
- The `401` body is the existing `unauthorized` chat error response (`docs/contracts/chat-stream.md`,
  fixture `http-401.json`), with a message that does not leak whether the problem was signature,
  expiry, or format (same "don't leak internals" posture as the login error in the spec).

## Example (illustrative, not literal bytes)

```http
POST /api/chat HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI5ZjJi...
Content-Type: application/json

{ "id": "...", "messages": [...] }
```
