-- Correct rows, more work than was needed. There is no index on
-- `customers.name`, so the planner cannot start from bob; what it does
-- instead is read every order and look its customer up by primary key.
-- The plan is `SCAN o` then `SEARCH c USING INTEGER PRIMARY KEY` -- the
-- index on orders(customer_id) is not used at all, because nothing filters
-- on that column.
SELECT o.total AS total
  FROM orders o
  JOIN customers c ON c.id = o.customer_id
 WHERE c.name = 'bob'
 ORDER BY o.id;
