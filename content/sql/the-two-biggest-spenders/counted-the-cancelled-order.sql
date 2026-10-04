-- No WHERE: the cancelled order counts as money taken, so bob is 5.25 richer
-- than he should be. The LIMIT is correct, so this isolates the one mistake --
-- the shape is right and one number is wrong, which is the hardest kind of
-- wrong to notice in a report.
SELECT c.name,
       ROUND(SUM(o.total), 2) AS spent
  FROM customers c
  JOIN orders o ON o.customer_id = c.id
 GROUP BY c.id
 ORDER BY spent DESC
 LIMIT 2;
