-- The right rows, and nothing left behind for anybody else to use. Which is
-- the situation the exercise exists to fix, reproduced exactly.
SELECT c.name AS name,
       ROUND(
           COALESCE(
               SUM(CASE WHEN o.status <> 'cancelled' THEN o.total END),
               0
           ),
           2
       ) AS spent
  FROM customers c
  LEFT JOIN orders o ON o.customer_id = c.id
 GROUP BY c.id
 ORDER BY name;
