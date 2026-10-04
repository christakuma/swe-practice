CREATE VIEW customer_totals AS
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
 GROUP BY c.id;

SELECT * FROM customer_totals ORDER BY name;
