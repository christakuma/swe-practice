SELECT COALESCE(city, 'unknown') AS city,
       COUNT(*) AS customers
  FROM customers
 GROUP BY COALESCE(city, 'unknown')
 ORDER BY city;
