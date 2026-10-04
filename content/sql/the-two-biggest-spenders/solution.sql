SELECT c.name,
       ROUND(SUM(o.total), 2) AS spent
  FROM customers c
  JOIN orders o ON o.customer_id = c.id
 WHERE o.status <> 'cancelled'
 GROUP BY c.id
 ORDER BY spent DESC
 LIMIT 2;
