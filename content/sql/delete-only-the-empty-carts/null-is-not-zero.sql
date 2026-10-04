-- The thoughtful wrong answer: it treats "we never counted" as "there was
-- nothing", and deletes the one cart whose contents are unknown. Written by
-- someone who knew NULL = 0 is not true and drew the wrong conclusion from it.
DELETE FROM carts
 WHERE items = 0 OR items IS NULL;
