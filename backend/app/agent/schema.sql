-- Agent state (specs/002-agent-core/data-model.md). Created idempotently on first use and at the
-- end of the seed; no foreign keys to store tables, so a store reseed never touches these rows.

CREATE TABLE IF NOT EXISTS conversation_state (
    conversation_id    text PRIMARY KEY,
    verified_order_ids int[] NOT NULL DEFAULT '{}',
    failed_attempts    int NOT NULL DEFAULT 0,
    locked             boolean NOT NULL DEFAULT false,
    updated_at         timestamptz NOT NULL DEFAULT now()
);

-- Failures per order across conversations, so a new chat id does not reset the lockout.
CREATE TABLE IF NOT EXISTS order_verification_failures (
    order_id        int PRIMARY KEY,
    failed_attempts int NOT NULL DEFAULT 0,
    locked_until    timestamptz,
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS service_requests (
    request_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id text NOT NULL,
    type            text NOT NULL
        CHECK (type IN ('return', 'exchange_defect', 'exchange_preference', 'complaint', 'handoff')),
    order_id        int,
    reason          text NOT NULL,
    eligibility     jsonb,
    status          text NOT NULL DEFAULT 'open',
    created_at      timestamptz NOT NULL DEFAULT now()
);
