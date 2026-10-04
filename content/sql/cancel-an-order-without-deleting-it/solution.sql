UPDATE orders
   SET status = 'cancelled'
 WHERE status = 'pending'
   AND placed_on < '2026-06-10';
