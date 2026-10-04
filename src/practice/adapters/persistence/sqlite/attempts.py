"""Attempts in SQLite, with the SQL written out and nothing generated.

Satisfies `practice.domain.ports.AttemptRepository`, structurally — it does not
import the port (ADR 0002). The second implementation of it, and the one that
makes the in-memory store's deep-copy semantics retrospectively correct: a use
case that mutated an aggregate after saving it "persisted" the change by accident
against a dict, and loses it here, where a row is only what the last `save` wrote.

Four decisions worth stating.

**Save is an upsert plus a rewritten event log.** An attempt is saved at least
twice — once when it starts, once when it is graded — and every command in between.
`ON CONFLICT DO UPDATE` touches only the columns that can change; the identity, the
start time and the policy are written once and never updated, because nothing on
the aggregate can change them and a statement that rewrote them would quietly make
that untrue. The event rows are deleted and reinserted wholesale rather than
appended to. Appending would be faster and would need the repository to know how
many events it had already stored, which is state about the database held outside
it; deleting and reinserting is the same answer whatever the row count, and the row
count here is at most a few dozen.

**One transaction per save, so the log cannot be half-rewritten.** The delete and
the inserts are in the `Database.connect()` transaction, and the foreign key with
`ON DELETE CASCADE` is what makes the attempt row the thing that owns its events.
That cascade is also why `PRAGMA foreign_keys=ON` is set on every connection and
not left to the schema — it is per-connection and off by default.

**Reads are ordered explicitly.** The in-memory store gets `history_for`'s order
from an insertion-ordered dict and the port's contract is the order, not the
mechanism; here it has to be an `ORDER BY`. On `started_at` then `id`, because two
attempts started inside the same clock tick are possible and a listing that
reshuffles between runs is a listing nobody can diff.

**Loading many attempts is two queries, not one per attempt.** `history_for` and
`active` fetch their rows and then fetch every event for that set in one go. The
obvious implementation calls `get` in a loop, which is correct, slower, and the
shape of query that stops being free the first time a progress page asks for a
hundred attempts.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Final

from practice.adapters.persistence.sqlite.mappers import (
    attempt_row,
    event_rows,
    to_attempt,
)

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Mapping, Sequence

    from practice.adapters.persistence.sqlite.connection import Database
    from practice.domain.attempt import Attempt
    from practice.domain.ids import AttemptId, ExerciseId

__all__ = ["SqliteAttemptRepository"]

_COLUMNS: Final = (
    "id",
    "exercise_id",
    "status",
    "started_at",
    "finished_at",
    "max_commands",
    "allowed_commands",
    "hints",
    "mode",
    "deadline_seconds",
    "declared_time",
    "declared_space",
    "verdict",
)

#: Only what `Attempt`'s own methods can change. `complete` sets the status, the
#: finish time and the verdict; `abandon` the first two; `declare_complexity` the
#: claim. Everything else is set in the constructor and has no setter, so leaving
#: it out of the UPDATE is not an optimisation — it is the schema agreeing with
#: the aggregate about what is immutable.
_MUTABLE: Final = (
    "status",
    "finished_at",
    "declared_time",
    "declared_space",
    "verdict",
)

_INSERT_ATTEMPT: Final = (
    f"INSERT INTO attempts ({', '.join(_COLUMNS)}) "  # noqa: S608  (a literal tuple)
    f"VALUES ({', '.join(f':{column}' for column in _COLUMNS)}) "
    f"ON CONFLICT (id) DO UPDATE SET "
    f"{', '.join(f'{column} = excluded.{column}' for column in _MUTABLE)}"
)

_EVENT_COLUMNS: Final = ("attempt_id", "position", "at", "kind", "payload")

_INSERT_EVENT: Final = (
    f"INSERT INTO attempt_events ({', '.join(_EVENT_COLUMNS)}) "  # noqa: S608
    f"VALUES ({', '.join(f':{column}' for column in _EVENT_COLUMNS)})"
)

_SELECT_ATTEMPT: Final = "SELECT * FROM attempts WHERE id = :id"

_SELECT_HISTORY: Final = (
    "SELECT * FROM attempts WHERE exercise_id = :exercise_id ORDER BY started_at, id"
)

_SELECT_ACTIVE: Final = (
    "SELECT * FROM attempts WHERE status = 'active' ORDER BY started_at, id"
)

#: Ordered by when they *finished* rather than when they started, which is the
#: order a history reads in and the order the streak is counted from. Two
#: attempts can finish inside one clock tick, so `id` breaks the tie and a
#: listing never reshuffles between runs.
_SELECT_COMPLETED: Final = (
    "SELECT * FROM attempts WHERE status = 'completed' ORDER BY finished_at, id"
)

_SELECT_EVENTS: Final = (
    "SELECT * FROM attempt_events WHERE attempt_id = :attempt_id ORDER BY position"
)


class SqliteAttemptRepository:
    """Every attempt ever started, in one table and its event log in another."""

    __slots__ = ("_database",)

    def __init__(self, database: Database) -> None:
        self._database = database

    # --- writing ------------------------------------------------------------

    def save(self, attempt: Attempt) -> None:
        """Insert or replace, atomically, including the whole event log."""
        row = attempt_row(attempt)
        events = event_rows(attempt)
        with self._database.connect() as connection:
            connection.execute(_INSERT_ATTEMPT, row)
            connection.execute(
                "DELETE FROM attempt_events WHERE attempt_id = :attempt_id",
                {"attempt_id": row["id"]},
            )
            connection.executemany(_INSERT_EVENT, events)

    # --- reading ------------------------------------------------------------

    def get(self, attempt_id: AttemptId) -> Attempt | None:
        """`None` rather than raising for an id nobody saved.

        Now the common case rather than the exceptional one: every attempt id
        from a database that has since been deleted lands here, and so does a
        stale URL from a browser tab left open across a reinstall.
        """
        with self._database.connect() as connection:
            row = connection.execute(
                _SELECT_ATTEMPT, {"id": str(attempt_id)}
            ).fetchone()
            if row is None:
                return None
            events = connection.execute(
                _SELECT_EVENTS, {"attempt_id": str(attempt_id)}
            ).fetchall()
        return to_attempt(_mapping(row), [_mapping(event) for event in events])

    def history_for(self, exercise_id: ExerciseId) -> Sequence[Attempt]:
        """Every attempt at one exercise, oldest first."""
        with self._database.connect() as connection:
            rows = connection.execute(
                _SELECT_HISTORY, {"exercise_id": str(exercise_id)}
            ).fetchall()
            return self._hydrate(connection, rows)

    def active(self) -> Sequence[Attempt]:
        """Every attempt that has been neither submitted nor abandoned.

        The table PLAN.md §8.1 says the resume prompt and `practice gc` need: an
        attempt is active until it finishes, its workspace lives exactly that
        long, and an orphan is a workspace with no row in here.
        """
        with self._database.connect() as connection:
            rows = connection.execute(_SELECT_ACTIVE).fetchall()
            return self._hydrate(connection, rows)

    def completed(self) -> Sequence[Attempt]:
        """Every graded attempt, oldest finish first. What `/progress` reads.

        No index behind it, deliberately. `attempts_active` is partial because
        every other status is dead weight in an index whose question is "which
        are still open"; the mirror image would be an index over almost the whole
        table, which SQLite would decline to use for a scan that returns almost
        the whole table anyway.
        """
        with self._database.connect() as connection:
            rows = connection.execute(_SELECT_COMPLETED).fetchall()
            return self._hydrate(connection, rows)

    def __len__(self) -> int:
        """How many attempts are stored, for a test that wants to say so."""
        with self._database.connect() as connection:
            return int(
                connection.execute("SELECT count(*) FROM attempts").fetchone()[0]
            )

    def __repr__(self) -> str:
        return f"SqliteAttemptRepository({self._database.path})"

    # --- the pieces ---------------------------------------------------------

    def _hydrate(
        self, connection: sqlite3.Connection, rows: Sequence[sqlite3.Row]
    ) -> tuple[Attempt, ...]:
        """Attach each attempt's events, in one query rather than one per attempt.

        The `IN` list is built from a placeholder per id, never by interpolating
        the ids themselves: they are uuids from the domain and could not carry
        anything interesting, but a query assembled by string concatenation is a
        habit, and the habit is the problem.
        """
        if not rows:
            return ()
        ids = [str(row["id"]) for row in rows]
        placeholders = ", ".join("?" * len(ids))
        events: dict[str, list[Mapping[str, object]]] = defaultdict(list)
        for event in connection.execute(
            "SELECT * FROM attempt_events "  # noqa: S608  (placeholders, not values)
            f"WHERE attempt_id IN ({placeholders}) ORDER BY attempt_id, position",
            ids,
        ):
            events[str(event["attempt_id"])].append(_mapping(event))
        return tuple(to_attempt(_mapping(row), events[str(row["id"])]) for row in rows)


def _mapping(row: sqlite3.Row) -> Mapping[str, object]:
    """A `sqlite3.Row` as something the mappers can read.

    `Row` indexes by column name but is not a `Mapping`, and the mappers take one
    deliberately: it is what lets them be unit-tested against a plain dict with
    no database in the test at all.
    """
    return {key: row[key] for key in row.keys()}  # noqa: SIM118  (Row has no __iter__ over keys)
