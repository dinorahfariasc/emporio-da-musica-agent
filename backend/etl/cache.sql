-- Shared objects that survive every seed; also created before the embedding step.
CREATE EXTENSION IF NOT EXISTS vector;

-- Persists across seeds: never dropped.
CREATE TABLE IF NOT EXISTS embedding_cache (
    provider    text NOT NULL,
    model       text NOT NULL,
    input_type  text NOT NULL CHECK (input_type IN ('document', 'query')),
    text_key    text NOT NULL,
    embedding   vector(768) NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, model, input_type, text_key)
);
