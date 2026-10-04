-- Right row, wrong verb. The order is gone rather than cancelled, so the
-- row count drops and finance has no record that it ever happened.
DELETE FROM orders
 WHERE status = 'pending'
   AND placed_on < '2026-06-10';
