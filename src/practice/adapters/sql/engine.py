"""Running one drill answer, and the four controls that make it safe to.

The SQL drill engine (PLAN.md §11, Phase 14). It takes a seed and an answer as
text and hands back a `DrillQuery` over the database they produced.

**Everything happens in `:memory:`, and that is the single decision the rest of
this module follows from.** The seed is executed into a fresh in-memory database
on *every* grading pass, and the answer runs against that. Four things fall out
of it, and the first is not a nicety:

* **Re-grading is idempotent by construction.** This matters more here than
  anywhere else in the project because of ADR 0013: own-editor mode grades on
  every Ctrl+S, so an answer is run tens of times. `INSERT INTO orders ...` run
  twice against a persistent database gives a different verdict the second time,
  and `UPDATE totals SET total = total * 2` gives a different one every time.
  The kata engine never had to think about this — pytest against a file is
  naturally idempotent — and a drill engine that kept a database file would have
  shipped a grader whose verdict depended on how often you had saved.
* **There is no file to confine.** The sandbox's whole blast-radius argument
  (§8.1) is about a path a command could escape; an in-memory database has no
  path, so the escape does not exist to be refused.
* **Nothing to clean up**, which on Windows is worth having: the project already
  absorbs one papercut from git marking objects read-only
  (`sandbox/workspace.py`), and an open SQLite file in a directory something is
  trying to delete is the same class of problem.
* **The seed stays readable on disk**, because the provisioner only ever copies
  it. That is deliberate rather than incidental: the solver is *meant* to read
  `seed.sql` — knowing the schema is part of the exercise, and a drill with a
  hidden schema would be a riddle.

**The policy is enforced by SQLite, not by matching the solver's text.** An
answer is untrusted input under §8.1's trust split, and the thing worth stopping
is `ATTACH DATABASE '/etc/passwd' AS x` — which reaches the filesystem the
in-memory database otherwise cannot. The obvious implementation is a regular
expression over the answer, and it is the wrong one for exactly the reason
ADR 0003 gives about grading: `/*c*/ATTACH` and `ATTACH/**/DATABASE` defeat a
pattern, and a pattern strict enough to catch them starts refusing the word
inside a string literal. `set_authorizer` is SQLite's own hook, runs during
preparation, and cannot be spelled around.

**Statements are split with `sqlite3.complete_statement` rather than on `;`.**
A semicolon inside a string literal or a comment is not a statement boundary,
and the stdlib already knows where one is. `executescript` was the alternative
and cannot be used: it commits, and it gives neither the final statement's rows
nor which statement failed.
"""

from __future__ import annotations

import sqlite3
import time
from typing import TYPE_CHECKING, Final

from practice.adapters.sql.drill_query import SqliteDrillQuery
from practice.domain.ports import ResultSet

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = ["DrillSeedError", "run_answer", "split_statements"]

#: How often the progress handler is consulted, in SQLite virtual-machine
#: instructions. Low enough that a runaway recursive CTE is stopped promptly,
#: high enough that the callback is not the cost of running a normal drill —
#: a drill's queries are over tens of rows and finish without it firing once.
_PROGRESS_INTERVAL: Final = 1_000

#: Actions denied to an answer. Both of them are about reaching another
#: database, which is the one thing an in-memory connection could otherwise do
#: that leaves the sandbox.
_DENIED: Final = frozenset({sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH})


class DrillSeedError(Exception):
    """The exercise's own seed did not run.

    An authoring bug, not a solver mistake, so it is an exception rather than a
    failing check — the same line `KataRunnerError` draws. A solver cannot act on
    "this exercise's schema is broken", and the graded replay in the content
    suite is what turns it into a build failure before anyone sees it.
    """


def split_statements(sql: str) -> tuple[str, ...]:
    """SQL text as a tuple of complete statements, comments and blanks dropped.

    Accumulates lines until `sqlite3.complete_statement` says the buffer is a
    statement, which is how the stdlib spells "find the boundary" and is correct
    about a `;` inside a string literal. A trailing fragment with no terminating
    semicolon is still returned: a solver who left the last `;` off meant the
    statement, and SQLite will run it.
    """
    statements: list[str] = []
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if buffer.strip() and sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        statements.append(buffer.strip())
    return tuple(statement for statement in statements if _is_executable(statement))


def _is_executable(statement: str) -> bool:
    """Whether a statement is anything other than comments and whitespace.

    A trailing `-- your answer here` in a stub is the common case, and counting
    it as a statement would make `statement_count` wrong and give
    `sql_matches` a line that is not SQL to search.
    """
    stripped = "\n".join(
        line
        for line in statement.splitlines()
        if line.strip() and not line.strip().startswith("--")
    )
    return bool(stripped.strip().strip(";").strip())


def run_answer(*, seed: str, answer: str, timeout_seconds: float) -> SqliteDrillQuery:
    """Build the database, run the answer against it, and hand back the query.

    **The caller owns the connection and must close it**, which is why this
    returns a `SqliteDrillQuery` rather than a verdict: `table()` and `tables()`
    are questions about a live database, so the connection has to outlive the
    call and die when grading is done. `ScenarioGrader` has the same shape for
    the same reason — a `RepoQuery` caches for the life of one pass and must not
    outlive it. `SqlDrillGrader` wraps this in `contextlib.closing`.

    The seed runs **before** the authorizer is installed, because it is trusted
    code in exactly the sense `Workspace.run_tool` is: an exercise author wrote
    it, and policing it would be policing the exercise rather than the answer.

    An answer that fails is not an error. The first statement to raise stops the
    run and its message becomes `DrillQuery.error`, so a solver sees
    `near "FORM": syntax error` in the panel. Statements before it have already
    taken effect, which is the honest thing to grade: that is the state SQLite
    was left in, and a drill asserting on a table will report it.
    """
    connection = sqlite3.connect(":memory:")
    try:
        _seed(connection, seed)
    except BaseException:
        connection.close()
        raise

    statements = split_statements(answer)
    result, error = _execute(connection, statements, timeout_seconds=timeout_seconds)
    plan = _plan(connection, statements) if error is None else ()
    return SqliteDrillQuery(
        connection,
        result=result,
        plan=plan,
        statements=statements,
        error=error,
    )


def _seed(connection: sqlite3.Connection, seed: str) -> None:
    """Execute the exercise's seed, or refuse the exercise."""
    try:
        connection.executescript(seed)
    except sqlite3.Error as exc:
        raise DrillSeedError(f"the drill's seed could not be run: {exc}") from exc


def _execute(
    connection: sqlite3.Connection,
    statements: Sequence[str],
    *,
    timeout_seconds: float,
) -> tuple[ResultSet | None, str | None]:
    """Run the answer under the authorizer and the deadline.

    Returns the **last** row-returning statement's result, so an answer that is
    a `CREATE TEMP VIEW` followed by a `SELECT` is graded on the `SELECT` — see
    `DrillQuery.result`. `None` means no statement returned rows, which is the
    normal case for a drill graded on `table` alone.
    """
    connection.set_authorizer(_authorizer)
    connection.set_progress_handler(_deadline(timeout_seconds), _PROGRESS_INTERVAL)
    try:
        result: ResultSet | None = None
        for statement in statements:
            try:
                cursor = connection.execute(statement)
            except sqlite3.Error as exc:
                return result, str(exc)
            if cursor.description is not None:
                result = _result_of(cursor)
        return result, None
    finally:
        # Both off before the caller gets the connection: the assertions then
        # read the database through `table()` and `tables()`, and those are
        # trusted queries this module wrote. Leaving the deadline armed would
        # abort them once a slow answer had used the budget up, which would
        # report a correct answer as having no tables.
        connection.set_progress_handler(None, 0)
        connection.set_authorizer(None)


def _authorizer(
    action: int,
    arg1: str | None,
    arg2: str | None,
    database: str | None,
    trigger: str | None,
) -> int:
    """SQLite's own preparation-time hook. Denies reaching another database.

    Everything else is allowed, deliberately. An answer that drops the table it
    was asked to update is not a security problem, it is a wrong answer, and
    `table_exists` is what reports it — refusing the statement would turn a
    gradeable mistake into a refusal and teach nothing.
    """
    del arg1, arg2, database, trigger
    return sqlite3.SQLITE_DENY if action in _DENIED else sqlite3.SQLITE_OK


def _deadline(timeout_seconds: float) -> Callable[[], int]:
    """A progress handler that aborts once the budget is spent.

    A monotonic clock rather than the injected `Clock` port: this is a wall-clock
    budget on a running query, the same thing `execution.py` gives a subprocess,
    and a test clock that stood still would mean no timeout at all. The `Clock`
    port exists so that *due dates* are deterministic, which is a different job.
    """
    expires_at = time.monotonic() + timeout_seconds

    def exceeded() -> int:
        return 1 if time.monotonic() > expires_at else 0

    return exceeded


def _plan(connection: sqlite3.Connection, statements: Sequence[str]) -> tuple[str, ...]:
    """`EXPLAIN QUERY PLAN` over the answer's final statement.

    The final one and not each of them, because that is the statement
    `DrillQuery.result` reports and the one a `query_plan_matches` advisory is
    about. Run after the answer, so a plan over a temp view the answer created
    resolves.

    A statement that will not explain produces no plan rather than an error.
    `EXPLAIN QUERY PLAN INSERT ...` is legal but uninteresting, and a drill
    asserting on a plan it was never going to get reports "there was no query
    plan", which says the right thing.
    """
    if not statements:
        return ()
    try:
        rows = connection.execute(f"EXPLAIN QUERY PLAN {statements[-1]}").fetchall()
    except sqlite3.Error:
        return ()
    return tuple(str(row[-1]) for row in rows)


def _result_of(cursor: sqlite3.Cursor) -> ResultSet:
    """A cursor's description and rows, as the port's value object."""
    columns = tuple(str(column[0]) for column in cursor.description)
    return ResultSet(columns=columns, rows=tuple(tuple(row) for row in cursor))
