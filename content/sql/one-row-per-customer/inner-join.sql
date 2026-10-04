-- The plausible wrong answer: an inner join, which silently drops every
-- customer the ON condition found nothing for.
SELECT c.name,
       COUNT(o.id) AS orders
  FROM customers c
  JOIN orders o ON o.customer_id = c.id
 GROUP BY c.id
 ORDER BY c.name;
