-- Schema owned by the ETL (specs/001-data-foundation/data-model.md).
-- Runs inside the seed transaction, after the owned tables were dropped (see etl/load.py).
-- Shared objects are created only if missing; owned tables are always created from scratch.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- There is no CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS. Being create-if-missing, a later
-- change to this mapping is NOT applied to an existing database: drop pt_unaccent by hand
-- (after the tables whose tsv columns use it) and re-seed.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'pt_unaccent') THEN
        CREATE TEXT SEARCH CONFIGURATION pt_unaccent (COPY = portuguese);
        ALTER TEXT SEARCH CONFIGURATION pt_unaccent
            ALTER MAPPING FOR asciiword, word, hword, hword_part, hword_asciipart, asciihword
            WITH unaccent, portuguese_stem;
    END IF;
END
$$;

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

CREATE TABLE categories (
    category_id  int PRIMARY KEY,
    name         text NOT NULL,
    description  text NOT NULL
);

CREATE TABLE products (
    product_id                  int PRIMARY KEY,
    category_id                 int NOT NULL REFERENCES categories,
    name                        text NOT NULL,
    price_brl                   numeric(10, 2) NOT NULL CHECK (price_brl > 0),
    stock_quantity              int NOT NULL CHECK (stock_quantity >= 0),
    status                      text NOT NULL
        CHECK (status IN ('active', 'discontinued', 'coming_soon')),
    specs                       jsonb NOT NULL,
    description                 text NOT NULL,
    description_trusted         boolean NOT NULL,
    availability                text NOT NULL
        CHECK (availability IN ('in_stock', 'out_of_stock', 'discontinued', 'coming_soon')),
    is_sellable                 boolean NOT NULL,
    effective_promotion_id      int,
    effective_discount_percent  int NOT NULL DEFAULT 0,
    promo_price_brl             numeric(10, 2) NOT NULL,
    created_at                  date NOT NULL
);

CREATE TABLE promotions (
    promotion_id      int PRIMARY KEY,
    product_id        int NOT NULL REFERENCES products,
    discount_percent  int NOT NULL CHECK (discount_percent BETWEEN 1 AND 100),
    description       text NOT NULL,
    is_active         boolean NOT NULL
);

-- products and promotions reference each other; checked at commit.
ALTER TABLE products
    ADD FOREIGN KEY (effective_promotion_id) REFERENCES promotions
    DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE customers (
    customer_id   int PRIMARY KEY,
    name          text NOT NULL,
    phone         text NOT NULL,
    phone_digits  text NOT NULL,
    email         text NOT NULL,
    email_shared  boolean NOT NULL,
    city          text NOT NULL
);

CREATE TABLE orders (
    order_id            int PRIMARY KEY,
    customer_id         int NOT NULL REFERENCES customers,
    order_date          date NOT NULL,
    status              text NOT NULL
        CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    payment_method      text NOT NULL
        CHECK (payment_method IN ('pix', 'boleto', 'debit', 'credit_3x', 'credit_6x', 'credit_12x')),
    total_brl           numeric(10, 2) NOT NULL,
    items_total_brl     numeric(10, 2) NOT NULL,
    total_mismatch      boolean NOT NULL,
    tracking_code       text,
    estimated_delivery  date,
    notes               text
);

CREATE TABLE order_items (
    order_id              int NOT NULL REFERENCES orders,
    product_id            int NOT NULL REFERENCES products,
    quantity              int NOT NULL CHECK (quantity > 0),
    product_not_on_sale  boolean NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
