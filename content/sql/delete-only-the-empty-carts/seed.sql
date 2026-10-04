-- Abandoned shopping carts, and the column that makes this interesting.
--
-- `items` is nullable, and the three states are NOT the same:
--   * a number means we counted that many items
--   * 0 means we counted, and there were none
--   * NULL means we never counted -- the cart predates the column
--
-- Only one of those three is a cart we know is empty.

CREATE TABLE carts (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    created_on  TEXT NOT NULL,
    items       INTEGER
);

INSERT INTO carts (id, customer_id, created_on, items) VALUES
    (1, 1, '2026-06-01', 3),
    (2, 2, '2026-06-18', 0),
    (3, 3, '2026-06-19', 2),
    (4, 4, '2026-06-02', NULL);
