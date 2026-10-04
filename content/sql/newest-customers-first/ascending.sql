-- Ordered, and the wrong way: ascending is the default, so "newest first"
-- is the direction you have to ask for.
SELECT name,
       signed_up
  FROM customers
 ORDER BY signed_up;
