-- 0003_attempt_mode — which rules an attempt was opened under, and its clock.
--
-- Phase 15's interview mode. `AttemptPolicy` is *the rules this attempt was
-- opened under, copied in at construction* (§4.3), and these two columns are the
-- two it gained: the mode, and the deadline the mode implies.
--
-- **Two `ADD COLUMN`s and no table rebuild, same as 0002** — but for the
-- opposite reason, and the difference is worth stating. 0002's columns are
-- nullable because NULL *means* something there: no FSRS has touched this card.
-- `mode` has no such reading. Every attempt already in the table was run under
-- the only rules that existed, so there is a correct value to backfill with and
-- it is `'practice'` — which is what a NOT NULL DEFAULT does in one statement.
-- A nullable `mode` would have invented a third state ("opened under unknown
-- rules") that nothing can interpret and every reader would have to branch on.
--
-- `deadline_seconds` is nullable because an untimed attempt genuinely has no
-- deadline, and that is every row written before this migration.
--
-- **The CHECKs are the schema's half of the two invariants `AttemptPolicy`
-- enforces**, for the reason 0001 states at length: the aggregate refuses to
-- reach an impossible state and the schema refuses to store one, so a mapper
-- that wrote the mode and dropped the deadline fails on the INSERT rather than
-- on the read — where it would surface as a policy that passed through
-- `__post_init__` in one direction and not the other.
--
-- SQLite applies a column CHECK as a table CHECK, which is why the pairing
-- constraint lives on the second column and references the first. The ordering
-- matters in one way only: `mode` has to exist before a CHECK can name it.
--
-- Note what is *not* here. There is no CHECK that an interview carries no hints,
-- because `hints` is a JSON array in a TEXT column (0001's third convention) and
-- a constraint over its contents would mean teaching this schema to parse JSON.
-- That invariant stays where it can be stated once and read: `AttemptPolicy`.

ALTER TABLE attempts
    ADD COLUMN mode TEXT NOT NULL DEFAULT 'practice'
        CHECK (mode IN ('practice', 'interview'));

ALTER TABLE attempts
    ADD COLUMN deadline_seconds INTEGER CHECK (
        (deadline_seconds IS NULL OR deadline_seconds >= 1)
        AND (deadline_seconds IS NULL) = (mode = 'practice')
    );
