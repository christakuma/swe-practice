"""A finished SQL drill in memory, for the ten assertions to be tested against.

The second implementation of `DrillQuery` (PLAN.md §13), and the one that makes
`tests/unit/domain/drills/` cost milliseconds instead of a SQLite file per case.

**It is built from rows, not from SQL**, which is the deliberate difference from
the real `SqliteDrillQuery`. A fake that ran the SQL would be a second,
worse SQLite driver and would prove nothing the real one does not; this one lets
a test state *the answer came back with these three rows and the table was left
holding those two* directly, which is the only thing the assertions read.

That also means the fake can be **wrong** in ways the real adapter cannot — an
answer with a result but also an error, a table whose rows have more cells than
its columns. That is the same property `FakeRepoQuery` has and the same reason:
a double that can only produce reachable states cannot be used to test what an
assertion does with an unreachable one, and an unreachable state is exactly what
a broken exercise produces.

The conformance suite in `tests/integration/sql/test_conformance.py` is what
holds the two implementations to the same answers on the states that *are*
reachable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.ports import ResultSet

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.domain.ports import Scalar

__all__ = ["FakeDrillQuery", "a_result"]


def a_result(
    columns: Sequence[str] = ("name", "orders"),
    rows: Sequence[Sequence[Scalar]] = (("alice", 2), ("bob", 0)),
) -> ResultSet:
    """A small result set, with the shape most assertion tests want.

    Defaults rather than required arguments because most cases are about one
    dimension — the row order, a missing column, a `NULL` — and spelling out a
    two-by-two table in every test is the noise that makes a suite unreadable.
    """
    return ResultSet(columns=tuple(columns), rows=tuple(tuple(row) for row in rows))


class FakeDrillQuery:
    """Satisfies `practice.domain.ports.DrillQuery` from values held in memory."""

    def __init__(
        self,
        *,
        result: ResultSet | None = None,
        tables: Mapping[str, ResultSet] | None = None,
        plan: Sequence[str] = (),
        statements: Sequence[str] = (),
        error: str | None = None,
    ) -> None:
        self._result = result
        self._tables = dict(tables or {})
        self._plan = tuple(plan)
        self._statements = tuple(statements)
        self._error = error

    def error(self) -> str | None:
        return self._error

    def result(self) -> ResultSet | None:
        return self._result

    def table(self, name: str) -> ResultSet | None:
        return self._tables.get(name)

    def tables(self) -> frozenset[str]:
        return frozenset(self._tables)

    def plan(self) -> tuple[str, ...]:
        return self._plan

    def statements(self) -> tuple[str, ...]:
        return self._statements
