-- The subtler wrong answer: the right join, and COUNT(*) instead of
-- COUNT(o.id). After the outer join dana still has one row -- made of her
-- own columns and a row of NULLs -- so COUNT(*) counts it and reports 1.
SELECT c.name,
       COUNT(*) AS orders
  FROM customers c
  LEFT JOIN orders o ON o.customer_id = c.id
 GROUP BY c.id
 ORDER BY c.name;
