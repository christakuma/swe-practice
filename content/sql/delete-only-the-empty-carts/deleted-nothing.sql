-- The one that looks right and matches no rows at all. `= NULL` is never
-- true, not even for a NULL -- so this runs cleanly, reports nothing, and
-- changes nothing.
DELETE FROM carts
 WHERE items = NULL;
