-- A view, correctly created, with the cancelled-order filter in the WHERE
-- clause instead of inside the aggregate. That is a different question: the
-- WHERE runs before the grouping, so bob's cancelled order is excluded (right)
-- and dana -- who has no orders at all -- is filtered out of existence by the
-- NULL status her outer join produced (wrong).
CREATE VIEW customer_totals AS
SELECT c.name AS name,
       ROUND(COALESCE(SUM(o.total), 0), 2) AS spent
  FROM customers c
  LEFT JOIN orders o ON o.customer_id = c.id
 WHERE o.status <> 'cancelled'
 GROUP BY c.id;

SELECT * FROM customer_totals ORDER BY name;
