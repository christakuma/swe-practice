-- The one that ruins an afternoon: no WHERE, so every order is cancelled.
-- Nothing in the result set would tell you -- an UPDATE returns no rows
-- whether it touched one of them or all six.
UPDATE orders
   SET status = 'cancelled';
