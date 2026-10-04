-- 0002_fsrs_memory_state — the two columns FSRS needs and SM-2 does not.
--
-- The first schema change, and `0001_initial.sql` predicted it ("the next schema
-- change is 0002") without knowing what it would be. This is it: Phase 13 added
-- `FsrsScheduler` behind the `Scheduler` port, and ADR 0008 had already named the
-- bill -- `ease` and `interval_days` are SM-2's working state, FSRS wants
-- stability and difficulty instead, and "an honest migration would add columns
-- rather than reuse them".
--
-- **Two `ADD COLUMN`s and no table rebuild**, which is what nullable buys. Every
-- row already in `review_cards` was written by SM-2 and gets NULL in both
-- columns, which is exactly what it means: no FSRS has touched this card. The
-- twelve-step rebuild SQLite's documentation describes would be needed to make
-- either column NOT NULL, and there is no value to backfill them with -- a
-- stability invented for a card whose history is three SM-2 reviews would be a
-- fabricated memory model, and `FsrsScheduler` would rather adopt the interval
-- the card actually carries (`domain/scheduling/fsrs.py`).
--
-- **The CHECKs are the schema's half of the same three invariants `ReviewCard`
-- enforces**, for the reason 0001 states at length: the aggregate refuses to
-- reach an impossible state and the schema refuses to store one, so a mapper
-- that dropped a column fails on the INSERT rather than on the read. SQLite
-- applies a column CHECK as a table CHECK, which is why the pairing constraint
-- can live on the second column and reference the first.
--
-- Note what the pairing constraint is *not* protecting against. Nothing here can
-- stop a card being written by SM-2, read by FSRS, and written back -- that is a
-- supported sequence, and `fsrs.py` is where it is handled. What it stops is
-- *half* a memory state, which is only ever a bug in this file or in the mapper.

ALTER TABLE review_cards
    ADD COLUMN stability REAL CHECK (stability IS NULL OR stability > 0);

ALTER TABLE review_cards
    ADD COLUMN difficulty REAL CHECK (
        (difficulty IS NULL OR (difficulty >= 1.0 AND difficulty <= 10.0))
        AND (stability IS NULL) = (difficulty IS NULL)
    );
