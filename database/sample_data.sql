-- ═══════════════════════════════════════════════════════════════
-- Sample data + Slow Query test cases
-- ═══════════════════════════════════════════════════════════════

INSERT INTO categories (category_name) VALUES
  ('Electronics'), ('Clothing'), ('Books'), ('Home & Garden'), ('Sports');

INSERT INTO users (email, full_name, status) VALUES
  ('alice@example.com', 'Alice Smith', 'active'),
  ('bob@example.com', 'Bob Jones', 'active'),
  ('carol@example.com', 'Carol White', 'inactive'),
  ('dave@example.com', 'Dave Brown', 'active'),
  ('eve@example.com', 'Eve Davis', 'active');

INSERT INTO products (name, price, category_id) VALUES
  ('Laptop Pro 15', 1299.99, 1),
  ('Wireless Mouse', 29.99, 1),
  ('Running Shoes', 89.99, 5),
  ('Python Cookbook', 45.00, 3),
  ('Garden Hose', 24.99, 4);

INSERT INTO stock (product_id, qty, warehouse) VALUES
  (1, 50, 'WH-EAST'), (2, 200, 'WH-WEST'),
  (3, 75, 'WH-EAST'), (4, 120, 'WH-CENTRAL'), (5, 30, 'WH-WEST');

INSERT INTO orders (user_id, product_id, total_amount, status, created_at) VALUES
  (1, 1, 1299.99, 'completed', NOW() - INTERVAL '10 days'),
  (2, 2, 29.99, 'pending', NOW() - INTERVAL '2 days'),
  (3, 3, 89.99, 'completed', NOW() - INTERVAL '5 days'),
  (4, 4, 45.00, 'pending', NOW() - INTERVAL '1 day'),
  (5, 5, 24.99, 'shipped', NOW() - INTERVAL '3 days'),
  (1, 3, 89.99, 'completed', NOW() - INTERVAL '20 days'),
  (2, 1, 1299.99, 'cancelled', NOW() - INTERVAL '15 days');


-- ═══════════════════════════════════════════════════════════════
-- SLOW QUERY TEST CASES (paste into Query Analyzer)
-- ═══════════════════════════════════════════════════════════════

-- TEST 1: SELECT * — Score ~34
-- SELECT * FROM orders o
-- JOIN users u ON o.user_id = u.user_id
-- JOIN products p ON o.product_id = p.product_id
-- WHERE o.status = 'pending'
-- ORDER BY o.created_at DESC;

-- TEST 2: Correlated Subquery — Score ~22
-- SELECT u.user_id, u.email,
--   (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.user_id) AS cnt,
--   (SELECT SUM(total_amount) FROM orders o WHERE o.user_id = u.user_id) AS spent
-- FROM users u WHERE u.status = 'active';

-- TEST 3: Function on column — Score ~48
-- SELECT order_id, total_amount FROM orders
-- WHERE YEAR(created_at) = 2024 AND MONTH(created_at) = 6;

-- TEST 4: Cartesian JOIN — Score ~12
-- SELECT p.name, c.category_name, s.qty
-- FROM products p, categories c, stock s WHERE p.price > 50;

-- TEST 5: Optimized version — Score ~91
-- SELECT u.user_id, u.email, COUNT(o.order_id) AS total_orders
-- FROM users u
-- INNER JOIN orders o ON u.user_id = o.user_id
-- WHERE o.created_at BETWEEN '2024-01-01' AND '2024-12-31'
--   AND o.status = 'completed'
-- GROUP BY u.user_id, u.email
-- ORDER BY total_orders DESC LIMIT 50;
