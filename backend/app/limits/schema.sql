-- Per-account rate limit and daily budget counters (specs/004-auth-limits-deploy/data-model.md).
-- Created idempotently, same pattern as app/agent/schema.sql. `user_id` is the `sub` claim from
-- the verified service JWT (app/auth/service_jwt.py); not a foreign key to a `users` table since
-- that table lives in the frontend's database access path, not the backend's.

CREATE TABLE IF NOT EXISTS rate_limit_minute (
    user_id       uuid NOT NULL,
    window_start  timestamptz NOT NULL,
    request_count int NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, window_start)
);

CREATE TABLE IF NOT EXISTS token_usage_daily (
    user_id     uuid NOT NULL,
    usage_date  date NOT NULL,
    tokens_used int NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, usage_date)
);
