-- 0005_failed_submissions — a failed submission is an event, and the attempt stays open.
--
-- ADR 0029. A failing verdict used to complete the attempt, so the next press
-- of Submit was refused with "attempt 4fcff95d is completed". Now only a pass
-- completes one; a failure is appended to the log as a `submission` event,
-- carrying its verdict, and the solver tries again.
--
-- **A fourth event kind rather than a column**, because there can be any
-- number of them and each one has a verdict: a counter on `attempts` would say
-- how many times somebody failed and not what failed, and the grade suggestion
-- and the tutor context both read the second.
--
-- **The table is rebuilt because SQLite cannot alter a CHECK.** `kind` is
-- constrained to the kinds the mapper knows, which is the schema refusing to
-- *store* an event nothing can read back (0001's convention). There is no
-- `ALTER TABLE ... ALTER CONSTRAINT`; the documented procedure is to create the
-- new shape, copy the rows, drop the old table and rename. It is safe here for
-- the two reasons it is ever safe: `attempt_events` is a child, so dropping it
-- breaks no foreign key pointing *at* it, and the runner wraps this file in one
-- transaction, so a failure part-way leaves the old table where it was.
--
-- No index to recreate: the primary key is the only one this table has ever
-- had, and it comes back with the CREATE.

CREATE TABLE attempt_events_new (
    attempt_id TEXT NOT NULL REFERENCES attempts (id) ON DELETE CASCADE,
    position   INTEGER NOT NULL,
    at         TEXT NOT NULL,
    kind       TEXT NOT NULL,
    payload    TEXT NOT NULL,

    PRIMARY KEY (attempt_id, position),
    CHECK (position >= 0),
    CHECK (kind IN ('command', 'hint', 'solution', 'submission'))
) STRICT;

INSERT INTO attempt_events_new (attempt_id, position, at, kind, payload)
    SELECT attempt_id, position, at, kind, payload FROM attempt_events;

DROP TABLE attempt_events;

ALTER TABLE attempt_events_new RENAME TO attempt_events;
