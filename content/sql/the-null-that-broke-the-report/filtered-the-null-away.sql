-- Makes the odd-looking row disappear by deleting the customer from the
-- report. The totals no longer add up to four and nothing in the output
-- says so, which is how this kind of bug survives for months.
SELECT city,
       COUNT(*) AS customers
  FROM customers
 WHERE city IS NOT NULL
 GROUP BY city
 ORDER BY city;
