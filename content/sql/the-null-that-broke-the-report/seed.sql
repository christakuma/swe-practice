-- The shop. Read this: the schema is the question, not the answer.
--
-- Four customers, six orders. Worth noticing before you start:
--   * dana has never placed an order
--   * dana's city was never recorded, so it is NULL rather than ''
--   * one order is cancelled, so it was placed but no money was taken
--
-- Dates are ISO-8601 text, which is how SQLite stores a date you can sort.

CREATE TABLE customers (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    city      TEXT,
    signed_up TEXT NOT NULL
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    placed_on   TEXT NOT NULL,
    total       REAL NOT NULL,
    status      TEXT NOT NULL
);

CREATE INDEX idx_orders_customer ON orders(customer_id);

INSERT INTO customers (id, name, city, signed_up) VALUES
    (1, 'alice', 'leeds', '2026-01-15'),
    (2, 'bob',   'york',  '2026-02-03'),
    (3, 'carol', 'leeds', '2026-03-21'),
    (4, 'dana',  NULL,    '2026-04-02');

INSERT INTO orders (id, customer_id, placed_on, total, status) VALUES
    (1, 1, '2026-05-01', 40.00, 'shipped'),
    (2, 1, '2026-05-09', 15.50, 'shipped'),
    (3, 2, '2026-05-11', 70.25, 'shipped'),
    (4, 3, '2026-06-02', 10.00, 'pending'),
    (5, 2, '2026-06-14',  5.25, 'cancelled'),
    (6, 1, '2026-06-20', 22.00, 'pending');
