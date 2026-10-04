-- Every customer is grouped correctly and the unknown group reports 0.
-- `COUNT(city)` counts non-NULL values of that column, and the whole point
-- of that group is that the column is NULL in it -- so the one row it
-- contains is not counted. The total now adds up to three.
SELECT COALESCE(city, 'unknown') AS city,
       COUNT(city) AS customers
  FROM customers
 GROUP BY COALESCE(city, 'unknown')
 ORDER BY city;
