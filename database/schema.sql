-- ═══════════════════════════════════════════════════════════════
-- QueryLens Sample E-Commerce Schema
-- Works with PostgreSQL and MySQL
-- ═══════════════════════════════════════════════════════════════

-- Users
CREATE TABLE IF NOT EXISTS users (
    user_id     SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    full_name   VARCHAR(100),
    phone       VARCHAR(20),
    address     TEXT,
    status      VARCHAR(20) DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Categories
CREATE TABLE IF NOT EXISTS categories (
    category_id   SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    parent_id     INT REFERENCES categories(category_id)
);

-- Products
CREATE TABLE IF NOT EXISTS products (
    product_id   SERIAL PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    description  TEXT,
    price        DECIMAL(10,2),
    category_id  INT REFERENCES categories(category_id),
    created_at   TIMESTAMP DEFAULT NOW()
);

-- Stock
CREATE TABLE IF NOT EXISTS stock (
    stock_id    SERIAL PRIMARY KEY,
    product_id  INT REFERENCES products(product_id),
    qty         INT DEFAULT 0,
    warehouse   VARCHAR(100)
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    order_id      SERIAL PRIMARY KEY,
    user_id       INT REFERENCES users(user_id),
    product_id    INT REFERENCES products(product_id),
    total_amount  DECIMAL(10,2),
    status        VARCHAR(30) DEFAULT 'pending',
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

-- ── INDEXES (Add these to test WITH vs WITHOUT index) ──────────
-- These are the "good" indexes — comment them out to simulate slow queries

CREATE INDEX IF NOT EXISTS idx_orders_status       ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_user_id      ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_product_id   ON orders(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at   ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_users_status        ON users(status);
CREATE INDEX IF NOT EXISTS idx_products_category   ON products(category_id);

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_orders_status_date
    ON orders(status, created_at DESC);
