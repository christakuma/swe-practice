-- Half the WHERE: cancels order 6 as well, which was placed on the 20th and
-- is nobody's business. The table still has six rows, so a row-count check
-- cannot see this one.
UPDATE orders
   SET status = 'cancelled'
 WHERE status = 'pending';
