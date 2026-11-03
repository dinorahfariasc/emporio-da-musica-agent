# Feature Specification: Auth, limits, cost controls and production deploy

**Feature Branch**: `004-auth-limits-deploy`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "004-auth-limits-deploy: Auth, limits, cost controls and production deploy. Replace the /login placeholder with real authentication: Auth.js credentials provider, no public sign-up, a create-user CLI/script to provision accounts. The Next.js BFF calls FastAPI with a short-lived HS256 service JWT. Per-user rate limiting (20 req/min) and daily token budget (200k tokens/day) stored in Postgres, reset at 00:00 America/Campo_Grande; a turn already streaming finishes, the next request is refused with 429. Fail-closed production config: missing/invalid required env vars must refuse to start or refuse requests. Also: Anthropic/OpenRouter workspace spend limit (documented), production deploy wiring, end-to-end verification with a real reviewer account. See docs/planning/backlog.md E5 (#10) and constitution.md principle V."

**Merge note (2026-11-01)**: a parallel draft of this spec (`docs/10-auth-limits-spec` branch) was
reviewed and folded in: the error-response shape here now matches the existing `#4` chat-stream
contract exactly (`docs/contracts/chat-stream.md`: `unauthorized`/`rate_limited`/
`budget_exhausted`, `retryAfterSeconds`), and a new User Story 4 below closes the conversation-id
residual risk already flagged in `docs/decision-log.md` DL-012 ("until #10 binds the chat id to a
user, anyone who knows a chat id sees the orders verified in it"). A sign-in lockout requirement
and clock-skew tolerance for the service credential were also adopted from that draft.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An reviewer logs in and chats (Priority: P1)

An reviewer (the person reviewing this project, or the candidate demoing it) opens the
production site, is sent to a login page, enters the username and password they were given out of
band, and reaches the chat. Reloading the page or returning later keeps them signed in until the
session naturally expires or they sign out.

**Why this priority**: without this, the public deployment is either open to anyone who finds the
URL (unacceptable per constitution V) or usable by nobody. This is the feature's reason to exist.

**Independent Test**: with no session cookie, visiting any chat page redirects to `/login`;
submitting a provisioned username/password reaches the chat and a follow-up visit to `/login` goes
straight to the chat instead of asking again.

**Acceptance Scenarios**:

1. **Given** no active session, **When** the reviewer opens the chat URL, **Then** they are
   redirected to `/login` with the chat destination preserved.
2. **Given** a provisioned account, **When** the reviewer submits the correct username and
   password, **Then** they land on the chat and can send a message that gets a real answer.
3. **Given** a provisioned account, **When** the reviewer submits a wrong password, **Then**
   login is refused with a message that does not reveal whether the username exists.
4. **Given** an active session, **When** the reviewer reloads or reopens the browser later within
   the session lifetime, **Then** they are still signed in.
5. **Given** an active session, **When** the reviewer signs out, **Then** the chat is no longer
   reachable until they sign in again.

---

### User Story 2 - The project owner provisions an reviewer account (Priority: P1)

Before sharing the production URL, the project owner runs a command-line step to create a login
for a named reviewer, without exposing any public sign-up page.

**Why this priority**: this is the only way an account comes into existence; without it, Story 1
cannot happen. There is no self-service registration (constitution V: no public sign-up).

**Independent Test**: running the provisioning step with a username and password, then
immediately signing in with those exact credentials from Story 1, succeeds; there is no reachable
page or endpoint that creates an account from the browser.

**Acceptance Scenarios**:

1. **Given** the production database, **When** the owner runs the account-creation step with a
   username and password, **Then** a new account exists that can sign in.
2. **Given** an existing username, **When** the owner re-runs the step with that same username,
   **Then** it fails clearly instead of silently overwriting or duplicating the account.
3. **Given** the deployed site, **When** anyone looks for a sign-up page or API, **Then** none
   exists.

---

### User Story 3 - The system stops a user who sends too much, too fast, or too expensively (Priority: P1)

A signed-in user who sends messages faster than the allowed rate, or whose cumulative token usage
for the day has reached the daily budget, is told to slow down or come back after the daily reset,
instead of the request silently going through or silently failing.

**Why this priority**: the chat calls a paid, rate-limited LLM API behind a single shared key; one
runaway client (a bug, a stress test, an abusive user) could exhaust the budget or the quota for
everyone else, and the agent itself cannot be trusted to enforce this (constitution I and V: limits
are computed by the system, never by the model).

**Independent Test**: scripting more than 20 requests within one minute from one account gets some
of them refused with a clear "too many requests, try again in..." response while a second account
sending at the same time is unaffected; simulating a day's worth of token usage for one account
then sending one more message gets it refused with a "daily limit reached, resets at..." response.

**Acceptance Scenarios**:

1. **Given** a user who has sent 20 requests in the current minute, **When** they send a 21st,
   **Then** it is refused with a 429 response and a message stating when they can retry.
2. **Given** a user already streaming an answer, **When** the per-minute or daily limit is reached
   mid-answer, **Then** that answer is allowed to finish; only the *next* request is refused.
3. **Given** a user whose combined input+output tokens for the current day have reached the daily
   budget, **When** they send another message, **Then** it is refused with a message stating the
   limit resets at the next local midnight (America/Campo_Grande).
4. **Given** the daily reset time has passed, **When** the same user sends a message, **Then** it
   is accepted again.
5. **Given** two different signed-in users, **When** one of them is rate- or budget-limited,
   **Then** the other is unaffected.

---

### User Story 4 - A conversation belongs to the person who is signed in (Priority: P1)

Order verification and conversation state produced during a chat are tied to the signed-in
account, not to the client-supplied conversation id alone, so a different person who happens to
send the same conversation id (by guessing, reusing a shared link, or opening dev tools) cannot
see or reuse another account's verified order data.

**Why this priority**: this closes a residual risk already called out while building the agent
(docs/decision-log.md DL-012): today, anyone who knows a chat id sees the orders verified in it.
Going to a public production URL without closing this is not acceptable under constitution V.

**Independent Test**: sign in as account A, verify an order in conversation C, then send a message
carrying the same conversation id C while signed in as account B; B must not see A's verified
order, and must be asked to verify again.

**Acceptance Scenarios**:

1. **Given** account A verified an order inside conversation id C, **When** account B sends a
   message using conversation id C, **Then** B's request is treated as a distinct conversation —
   no order data verified by A is disclosed to B.
2. **Given** a chat request reaches the system without valid proof of a signed-in account (e.g. a
   direct call that bypasses the website), **Then** it is rejected before any conversation state is
   read or written.
3. **Given** valid proof of sign-in that is older than its short lifetime, **Then** the request is
   rejected, even if the conversation id is correct.

---

### User Story 5 - The production deployment fails safe, not open (Priority: P2)

If a required piece of production configuration (the secret used to trust requests between the
website and the backend, the database connection, or an LLM provider key) is missing or invalid,
the system refuses to start or refuses every request, instead of quietly running in an insecure or
broken mode.

**Why this priority**: a misconfiguration that fails *open* (e.g., accepting any request as
authenticated because the shared secret is empty) is a worse outcome than downtime, and is the
kind of mistake that is easy to make once during a rushed deploy.

**Independent Test**: deploying with the inter-service trust secret unset (or deliberately mismatched
between the two services) makes every chat request fail with a server error, never a request that
is silently treated as authenticated.

**Acceptance Scenarios**:

1. **Given** the backend starts without its required secrets/config, **When** it comes up,
   **Then** it does not serve chat requests (refuses to start, or every request to the chat
   endpoint fails closed).
2. **Given** a request to the backend that is missing or has an invalid inter-service credential,
   **When** the backend evaluates it, **Then** it is rejected and never treated as coming from an
   authenticated user.
3. **Given** the production environment variables are all present and valid, **When** the site is
   exercised end-to-end by a real reviewer account, **Then** login, chat, rate limiting and the
   daily budget all behave as specified above in the live deployment, not only in local tests.

---

### Edge Cases

- A user's browser session cookie is valid but the account was deleted or disabled after login:
  the next request must be treated as unauthenticated, not silently allowed.
- Clock/timezone edge: a request arriving at 23:59:59 and 00:00:01 America/Campo_Grande on the
  same connection must be counted against the correct day's budget.
- The shared secret used between the website and the backend is rotated: requests signed with the
  old secret must stop being accepted (no silent indefinite grace period) once the new secret is
  deployed everywhere.
- A user opens the chat in two tabs at once: the rate limit and the daily budget are per account,
  not per tab/session, so both tabs draw from the same counters.
- The database used for login/limits is briefly unreachable: the system must fail closed (refuse
  the request) rather than fail open (let every request through unauthenticated or unmetered).
- An reviewer account's password is forgotten: there is no self-service reset; the project owner
  re-provisions the account (acceptable for this scale, see Assumptions).
- Repeated wrong passwords for one username (brute force / typo loop): after 5 failed attempts
  within 15 minutes, further sign-in attempts for that username are refused for 15 minutes, even
  with the correct password.
- Small clock drift between the website and the chat-answering system: proof of sign-in MUST
  tolerate at most 30 seconds of clock skew without being rejected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST require a signed-in session to reach the chat; an unauthenticated
  visitor MUST be redirected to a login page.
- **FR-002**: The system MUST authenticate with a username and password checked against accounts
  stored in the production database; passwords MUST be stored hashed, never in plain text.
- **FR-003**: The system MUST NOT expose any way for a visitor to create their own account
  (no public sign-up page or endpoint).
- **FR-004**: The system MUST provide a command-line way for the project owner to create an
  account with a username and password, runnable against the production database, that fails
  clearly instead of duplicating or silently overwriting an existing username.
- **FR-005**: A failed login attempt MUST be refused with a generic message that does not reveal
  whether the username exists. After 5 failed attempts for one username within 15 minutes, further
  attempts for that username MUST be refused for 15 minutes regardless of password correctness.
- **FR-006**: A signed-in session MUST persist across page reloads and new browser visits until it
  expires or the user signs out.
- **FR-007**: The system MUST provide a way to sign out that ends the session.
- **FR-008**: The system that answers chat requests MUST only accept requests that carry proof the
  caller already passed sign-in (an inter-service credential issued after login); it MUST NOT
  accept a user's password or re-check login itself.
- **FR-009**: Proof of sign-in passed between the website and the chat-answering system MUST be
  short-lived (at most a few minutes), MUST tolerate at most 30 seconds of clock skew, and MUST be
  rejected once expired, missing, or invalid, using the existing `401 unauthorized` chat error
  response (`docs/contracts/chat-stream.md`).
- **FR-009a**: The chat-answering system MUST scope conversation state (including verified order
  access) to the combination of signed-in account **and** conversation id, never to the
  conversation id alone, so that knowing or guessing a conversation id never discloses another
  account's verified order data (closes the residual risk in `docs/decision-log.md` DL-012).
- **FR-010**: The system MUST track, per signed-in account, the number of chat requests made in
  the current minute and refuse additional requests beyond 20 per minute using the existing
  `429 rate_limited` chat error response, including a retry-after duration.
- **FR-011**: The system MUST track, per signed-in account, the combined input and output tokens
  consumed for the current local day (America/Campo_Grande) — every paid model call made for that
  account's turn, including a paid router/decider call, but excluding embedding calls (currently
  free-tier) — and refuse new chat requests once 200,000 tokens have been consumed, using the
  existing `429 budget_exhausted` chat error response, stating when the budget resets.
- **FR-012**: The daily token budget MUST reset at 00:00 America/Campo_Grande.
- **FR-013**: A chat turn already streaming when a limit is reached MUST be allowed to finish;
  only the next request is refused.
- **FR-014**: Rate limit and daily budget state MUST be tracked per account, not per browser
  session/tab/device, and MUST NOT be resettable or bypassable by the client (e.g. by opening a
  new tab or clearing cookies).
- **FR-015**: If a required production setting (inter-service secret, database connection, or LLM
  provider key) is missing or invalid, the system MUST refuse to start or MUST refuse every chat
  request rather than serve requests in an unauthenticated or unmetered mode.
- **FR-016**: The production deployment MUST document the environment variables and deploy/redeploy
  steps needed to run this feature, and the provider-side workspace spend limit used as a backstop
  (configured outside this repo, documented here).
- **FR-017**: The production deployment MUST be verified end-to-end with a real reviewer account:
  login, a real chat answer, a rate-limit refusal, and (where practical without waiting a full day)
  a simulated daily-budget refusal.

### Key Entities

- **Account**: an reviewer's login identity — username, hashed password, created-at. One or a
  handful of these exist for the whole deployment; there is no self-service lifecycle beyond
  creation and (via re-running the CLI or a manual deletion) removal.
- **Rate/budget counters**: per-account request count for the current minute and per-account
  token total for the current local day, with the day boundary in America/Campo_Grande. Reused
  fields from existing agent telemetry (prompt/completion tokens per turn) rather than a new
  accounting source.
- **Service credential**: the short-lived, signed proof that a chat request was issued by the
  website on behalf of an already-authenticated session; carries at least the account identity and
  an expiry.
- **Sign-in attempt record**: username, recent failure count and window, used to enforce the
  5-attempts/15-minutes lockout.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An unauthenticated visit to any chat URL in production reaches a login page 100% of
  the time; no chat content or tool result is ever visible before sign-in.
- **SC-002**: A provisioned reviewer can go from the login page to a real, working answer in
  production in under 1 minute.
- **SC-003**: Across 25 rapid requests from one account within a minute, no more than 20 succeed;
  the rest receive a clear "try again" response instead of an error page or a hang.
- **SC-004**: An account that reaches its daily token budget cannot consume further LLM spend that
  day; this is enforced even if the user retries, reloads, or uses a different device with the
  same account.
- **SC-005**: Simulating a missing or invalid inter-service secret in a non-production check shows
  100% of chat requests rejected, with zero requests treated as authenticated.
- **SC-006**: The production URL, shared with an reviewer who has never seen the project, lets
  them sign in and have a working conversation without the project owner needing to be present.
- **SC-007**: Two different signed-in accounts that happen to use the same conversation id never
  see each other's verified order data, demonstrated by a test with two accounts and one shared id.

## Assumptions

- Scale is one to a handful of named reviewer accounts (this is a solo project, not
  a multi-tenant product); no self-service registration, password reset, or account-management UI
  is in scope. The project owner re-provisions an account by re-running the CLI step if needed.
- "Fail closed" means: on missing/invalid required config, prefer refusing traffic over guessing a
  default that could be insecure (e.g. an empty or well-known shared secret, or an open CORS/auth
  bypass).
- The per-user rate limit (20 requests/minute) and daily token budget (200,000 input+output
  tokens/day) and the America/Campo_Grande reset time are carried over unchanged from the existing
  backlog decision (E5/#10) and constitution principle V; this spec does not revisit those numbers.
- Session lifetime, exact login UI copy, and token-expiry duration for the inter-service credential
  are implementation details for the plan, within "short-lived" (minutes, not hours) for the
  service credential and a standard multi-day session for the browser login.
- The provider workspace spend limit (Anthropic/OpenRouter) is a dashboard setting outside this
  repository; this feature only requires it to be configured and the value documented, not
  enforced in code.
- Out of scope for this feature: multi-factor auth, OAuth/social login, role-based permissions
  (all reviewer accounts are equivalent), and per-request (as opposed to per-minute/per-day)
  pricing controls.
