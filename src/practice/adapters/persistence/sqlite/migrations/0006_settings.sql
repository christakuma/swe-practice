-- 0006_settings -- the first thing in this database that is a choice rather than a record.
--
-- Review scheduling becomes optional and a track can carry a finish-by date;
-- both are a person's preference, not something derived from an attempt.
--
-- **One key-value table rather than a column or table per setting**: the two
-- settings share nothing but being small and the user's, and a table each would
-- be a migration for every preference added. Values are text and the meaning of
-- a key lives in `application/preferences.py`. Nothing here references another
-- table, so dropping a setting can never orphan a row.

CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL,

    CHECK (key <> '')
) STRICT;
