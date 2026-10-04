"""`DrillQuery` over a live SQLite connection. The real half of the port.

Satisfies `practice.domain.ports.DrillQuery` structurally, like every adapter
here (ADR 0002). `FakeDrillQuery` in `tests/fakes/drill.py` is the other
implementation, and `tests/integration/sql/test_conformance.py` is what holds
the two to the same answers — the same arrangement `RepoQuery` has, and for the
same reason: a fake allowed to differ makes its tests prove nothing.

**Two of the six methods are answers already computed, and four are live
queries**, which is the split worth understanding before changing anything here.
`result`, `plan`, `statements` and `error` describe what happened while the
answer ran and are handed in by `engine.run_answer` — they cannot be recovered
from the database afterwards. `table` and `tables` ask the database now, which
is why this object holds the connection and why the caller has to close it.

**Identifier interpolation is checked rather than quoted-and-hoped.** SQLite has
no parameter binding for a table name, so `table()` has to put the name into the
SQL text. The protection is not the quoting: it is that the name is first looked
up in `sqlite_master` *through a bound parameter*, and only a name that came back
from that lookup is interpolated. A name that is not a table in this database
never reaches the second query at all, so there is nothing for a crafted name to
be injected into — and since both the name and the database are gone when
grading ends, the blast radius of being wrong about it is one in-memory
database. Quoting is applied too, because a legitimate table called `order` is
a reserved word.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from practice.domain.ports import ResultSet

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["SqliteDrillQuery"]


class SqliteDrillQuery:
    """Satisfies `practice.domain.ports.DrillQuery` over an in-memory database."""

    __slots__ = ("_connection", "_error", "_plan", "_result", "_statements", "_tables")

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        result: ResultSet | None,
        plan: Sequence[str],
        statements: Sequence[str],
        error: str | None,
    ) -> None:
        self._connection = connection
        self._result = result
        self._plan = tuple(plan)
        self._statements = tuple(statements)
        self._error = error
        self._tables: frozenset[str] | None = None

    # --- what happened while the answer ran -------------------------------

    def error(self) -> str | None:
        return self._error

    def result(self) -> ResultSet | None:
        return self._result

    def plan(self) -> tuple[str, ...]:
        return self._plan

    def statements(self) -> tuple[str, ...]:
        return self._statements

    # --- what the database holds now --------------------------------------

    def tables(self) -> frozenset[str]:
        """Every table and view, excluding SQLite's own bookkeeping.

        `sqlite_%` names are filtered out because `sqlite_sequence` appears the
        moment a drill uses `AUTOINCREMENT` and is not a table anybody wrote.
        A `table_exists` failure lists what is there (`domain/drills/tables.py`),
        and an internal name in that list is noise in the one message that has
        to be readable.

        Memoised, because `table_exists` and every `table_matches` in a drill
        ask it, and the answer cannot change while grading — the connection is
        read-only in practice from here on. The same caching argument
        `GitRepoQuery` makes, with the same safety condition: the object does not
        outlive the pass.
        """
        if self._tables is None:
            rows = self._connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            self._tables = frozenset(str(row[0]) for row in rows)
        return self._tables

    def table(self, name: str) -> ResultSet | None:
        """Every row of one table, in `rowid` order, or `None` if it is not there.

        Declared column order and `rowid` row order, which is what makes an
        author's literal rows comparable without the drill specifying an
        `ORDER BY` it never wrote. A view has no `rowid`, so the order there is
        whatever the view produces — stated rather than hidden, because a drill
        asserting `ordered: true` over a view is asserting something SQLite does
        not promise.
        """
        if name not in self.tables():
            return None
        quoted = name.replace('"', '""')
        try:
            # Safe by the lookup above, not by the quoting: `name` is one of the
            # strings `sqlite_master` just returned. See the module docstring.
            cursor = self._connection.execute(f'SELECT * FROM "{quoted}"')  # noqa: S608
        except sqlite3.Error:
            # A view whose definition broke when the answer dropped a table it
            # selected from. `None` is right: the thing is not readable, which is
            # what the assertion needs to report, and a traceback in a verdict
            # panel teaches nothing (§6.5).
            return None
        columns = tuple(str(column[0]) for column in cursor.description)
        return ResultSet(columns=columns, rows=tuple(tuple(row) for row in cursor))

    # --- lifetime ---------------------------------------------------------

    def close(self) -> None:
        """Drop the in-memory database. Safe to call twice.

        A plain method rather than `__enter__`/`__exit__` so the grader can wrap
        it in `contextlib.closing` and this class stays a `DrillQuery` and
        nothing else — the port does not mention a lifetime, and an adapter that
        added one to the protocol would be making every fake implement it.
        """
        self._connection.close()
