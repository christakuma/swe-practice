-- 0001_initial — attempts, their event log, and review cards.
--
-- One migration rather than three, because this is the schema the first release
-- ships with: numbered files earn their keep from the first *change*, and
-- splitting the initial state into steps nobody ever ran separately would be
-- inventing a history. The next schema change is 0002.
--
-- No `BEGIN`/`COMMIT` in here. The runner wraps each migration in one
-- transaction of its own, so a file that opened another would commit half of it
-- (adapters/persistence/sqlite/connection.py).
--
-- Three conventions hold throughout:
--
--   * Timestamps are stored as the ISO 8601 strings `datetime.isoformat()`
--     produces, offset included, and are only ever compared for equality or
--     ordering. SQLite has no datetime type, and an integer epoch would lose the
--     offset -- which `Attempt` refuses to guess at for exactly the reason a
--     stored attempt must not come back with a duration of minus seven hours.
--   * Value objects are stored as their `str()` form: an `ExerciseId` is
--     `git/revert-a-pushed-commit`, an `AttemptId` is its uuid, a `Sha` is its
--     hex. Each one validates on construction, so the mapper re-validates every
--     row on the way back in and a corrupt value fails loudly at the boundary.
--   * Anything with structure -- the hint list, the allowlist, one event, a
--     verdict -- is JSON in a TEXT column. The alternative is five more tables
--     for data that is never queried by its parts, only loaded whole with its
--     attempt.
--
-- Every table is `STRICT`, so a column declared TEXT refuses an integer instead
-- of silently keeping it. Without that, SQLite's default type affinity would let
-- a mapper that forgot a `str()` store a value the mapper on the way back cannot
-- parse, and the row would look fine until something read it.
--
-- The CHECK constraints restate invariants the `Attempt` aggregate already
-- enforces. Deliberate duplication, with different jobs: the aggregate refuses
-- to *reach* an impossible state, and the schema refuses to *store* one, so a
-- mapper bug fails on the INSERT that would have written the contradiction
-- rather than on the read that eventually loads it back.

CREATE TABLE attempts (
    id                 TEXT PRIMARY KEY NOT NULL,
    exercise_id        TEXT NOT NULL,
    status             TEXT NOT NULL,
    started_at         TEXT NOT NULL,
    finished_at        TEXT,

    -- The policy, copied in when the attempt was constructed. Stored rather
    -- than re-derived from the exercise on load, because that is the whole
    -- point of `AttemptPolicy`: an attempt is graded under the rules it was
    -- started under, and an exercise edited mid-attempt must not retroactively
    -- change what a finished attempt was allowed to do.
    max_commands       INTEGER NOT NULL,
    allowed_commands   TEXT NOT NULL,
    hints              TEXT NOT NULL,

    -- Both axes or neither: a claim about one cannot disagree with an
    -- expectation about two (`ComplexityClaim`).
    declared_time      TEXT,
    declared_space     TEXT,

    verdict            TEXT,

    CHECK (status IN ('active', 'completed', 'abandoned')),
    CHECK (max_commands >= 0),
    -- An attempt is active until it is submitted or abandoned, and finishing is
    -- the thing that gives it an end timestamp (PLAN.md 8.1).
    CHECK ((status = 'active') = (finished_at IS NULL)),
    -- A verdict comes from `complete()` and from nowhere else, so an abandoned
    -- attempt cannot have one and a completed one cannot lack one.
    CHECK ((status = 'completed') = (verdict IS NOT NULL)),
    CHECK ((declared_time IS NULL) = (declared_space IS NULL))
) STRICT;

-- `history_for` is the only query that filters by exercise, and it is the one a
-- progress page runs per exercise.
CREATE INDEX attempts_exercise_id ON attempts (exercise_id, started_at);

-- `active()` is read on startup to offer resume-or-abandon, and by `gc` to
-- decide which workspace is still in use. Partial, because every other status
-- is dead weight in an index whose only question is "which are still open".
CREATE INDEX attempts_active ON attempts (started_at) WHERE status = 'active';

CREATE TABLE attempt_events (
    attempt_id TEXT NOT NULL REFERENCES attempts (id) ON DELETE CASCADE,
    -- Position in the log rather than a timestamp key: two events can share a
    -- timestamp (`Attempt` requires non-decreasing, not strictly increasing),
    -- and the order the log was appended in is the thing replay depends on.
    position   INTEGER NOT NULL,
    at         TEXT NOT NULL,
    kind       TEXT NOT NULL,
    payload    TEXT NOT NULL,

    PRIMARY KEY (attempt_id, position),
    CHECK (position >= 0),
    CHECK (kind IN ('command', 'hint', 'solution'))
) STRICT;

CREATE TABLE review_cards (
    exercise_id      TEXT PRIMARY KEY NOT NULL,
    state            TEXT NOT NULL,
    ease             REAL NOT NULL,
    interval_days    INTEGER NOT NULL,
    reps             INTEGER NOT NULL,
    lapses           INTEGER NOT NULL,
    -- A date, not a timestamp: `due_on` is a calendar day, and storing it as
    -- `YYYY-MM-DD` keeps `due_on(day)` a string comparison that cannot be
    -- thrown off by a time-of-day component.
    due_on           TEXT NOT NULL,
    last_reviewed_at TEXT,

    CHECK (state IN ('new', 'learning', 'review', 'lapsed')),
    -- SM-2's own floor, enforced in `ReviewCard` as well. The scheduler is not
    -- the sole writer -- a repository is -- and an invariant that holds only
    -- while one function writes it is not an invariant.
    CHECK (ease >= 1.3),
    CHECK (interval_days >= 0),
    CHECK (reps >= 0 AND lapses >= 0)
) STRICT;

-- What `due_on(day)` scans. The due queue is the dashboard's first query and
-- the only one that is a range scan rather than a lookup by key.
CREATE INDEX review_cards_due_on ON review_cards (due_on);
