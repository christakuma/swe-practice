-- 0004_current_attempt — which attempt the solver has in front of them.
--
-- ADR 0026. A tutor asked about "my attempt" with several open had nothing to
-- choose by, and ADR 0024 refused to guess. This is the thing to choose by: one
-- id, written by `MarkCurrentAttempt` when a solver turns to an attempt and
-- read back by `FindCurrentAttempt`.
--
-- **A table of its own rather than a column on `attempts`**, for two reasons
-- that are the same reason seen twice. It is not a fact about any one attempt
-- -- "current" is a relation between all of them, and a boolean per row would
-- need a second statement to clear the old one and a partial unique index to
-- stop two rows claiming it. And it is not part of the aggregate: a column on
-- `attempts` would either join `_COLUMNS` and be rewritten by every `save`, or
-- sit beside them as the one column the mappers do not know about.
--
-- **One row, and the CHECK is what makes it one.** `slot` can only be 1, so the
-- primary key refuses a second row and "mark" is an upsert on a key that is
-- always the same.
--
-- **No foreign key, deliberately.** The id here is allowed to outlive what it
-- meant: the attempt it names is submitted or abandoned in the ordinary course
-- of things, and the one reader already decides what each of those means. A
-- reference that kept the row honest about *existence* would add a constraint
-- for the one case -- a row deleted by hand -- that reader also handles.

CREATE TABLE current_attempt (
    slot       INTEGER PRIMARY KEY NOT NULL CHECK (slot = 1),
    attempt_id TEXT NOT NULL
) STRICT;
