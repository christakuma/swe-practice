"""What the answer returned. Five of the ten drill assertions.

The family that grades a `SELECT`, and the one most drills are built from.
Everything here reads `DrillQuery.result()` and nothing here touches a table —
which is the split `tables.py` is the other half of.

**`result_matches` compares as a multiset by default, and that default is the
interesting decision.** `SELECT name, orders FROM ...` with no `ORDER BY`
returns rows in whatever order SQLite finds convenient, and that order is not
part of the answer: two solvers who wrote the same correct query may legitimately
get different orderings, and a grader that failed one of them would be grading an
implementation detail. So row order is ignored unless the drill says
`ordered: true` — which it says exactly when the prompt asked for an order, and
at that point the order *is* the answer.

Every one of these answers `passed: False` with a readable `actual` where the
answer did not run, rather than raising (PLAN.md §6.5). A solver whose SQL has a
typo gets `near "FORM": syntax error` in the panel, which is the most useful
sentence available.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from practice.domain.checks.evaluation import CheckResult, compare
from practice.domain.drills.evaluation import (
    NO_RESULT,
    as_rows,
    as_text,
    describe_rows,
    expected_rows,
    single_row,
)

if TYPE_CHECKING:
    from practice.domain.drills.evaluation import DrillContext
    from practice.domain.ports import ResultSet

__all__ = [
    "result_columns",
    "result_contains_row",
    "result_matches",
    "result_ordered_by",
    "result_row_count",
]


def _result(context: DrillContext) -> ResultSet | None:
    """The answer's rows, or `None` — including when it did not run at all.

    Collapsing "errored" and "returned nothing" into one `None` here is safe
    because every caller reports the distinction itself through `_why_not`: the
    error message when there is one, `NO_RESULT` when there is not. The grader
    also raises a required `answer-ran` check ahead of all of these, so a
    syntax error never arrives as five identical row failures.
    """
    return context.query.result()


def _why_not(context: DrillContext) -> str:
    error = context.query.error()
    return f"<{error}>" if error is not None else NO_RESULT


def result_matches(context: DrillContext) -> CheckResult:
    """`result_matches {rows, ordered?}` — the answer returned exactly these rows.

    The assertion most drills are graded on, and the whole of the core bet for
    this kind: it compares *rows*, so two answers that reach them by different
    SQL are the same answer. A multiset comparison unless `ordered: true` — see
    the module docstring.
    """
    wanted = expected_rows(context.params)
    ordered = context.params.flag("ordered", default=False)
    result = _result(context)
    shape = "in this order" if ordered else "in any order"

    if result is None:
        return CheckResult(
            passed=False,
            expected=f"{describe_rows(wanted)} ({shape})",
            actual=_why_not(context),
        )

    found = as_rows(result)
    passed = found == wanted if ordered else Counter(found) == Counter(wanted)
    return CheckResult(
        passed=passed,
        expected=f"{describe_rows(wanted)} ({shape})",
        actual=describe_rows(found),
    )


def result_row_count(context: DrillContext) -> CheckResult:
    """`result_row_count {equals|at_least|at_most}` — how many rows came back.

    Worth having beside `result_matches` rather than being subsumed by it,
    because the two say different things to a solver. "One row per customer" is
    a claim about the *grain* of a query — the thing a careless join breaks — and
    a drill can assert it as a separate, separately-labelled check so that a
    duplicated row reports as "you have 12 rows for 8 customers" instead of as a
    wall of mismatched data.
    """
    operator, wanted = context.params.comparison()
    result = _result(context)
    if result is None:
        return CheckResult(
            passed=False,
            expected=f"a result with {operator.replace('_', ' ')} {wanted} row(s)",
            actual=_why_not(context),
        )
    return CheckResult(
        passed=compare(operator, result.row_count, wanted),
        expected=f"{operator.replace('_', ' ')} {wanted} row(s)",
        actual=f"{result.row_count} row(s)",
    )


def result_contains_row(context: DrillContext) -> CheckResult:
    """`result_contains_row {row}` — this one row is in the answer somewhere.

    The weaker sibling of `result_matches`, for the drill where one row is the
    lesson and the rest are scenery. The case it was written for is the outer
    join: *the customer who has placed no orders still gets a row, with zero* is
    one row out of eight, and asserting it on its own means the verdict names
    the row that is missing rather than printing eight that are nearly right.

    Also the natural pairing with `not: true`, which is how a drill says *this
    row must not be here* — the deleted record, the filtered-out NULL.
    """
    row = single_row(context.params, "row")
    result = _result(context)
    if result is None:
        return CheckResult(
            passed=False,
            expected=f"a row {', '.join(row)}",
            actual=_why_not(context),
        )

    found = as_rows(result)
    return CheckResult(
        passed=row in found,
        expected=f"a row {', '.join(row)}",
        actual=describe_rows(found),
    )


def result_columns(context: DrillContext) -> CheckResult:
    """`result_columns {columns, ordered?}` — the answer selected these columns.

    What makes `SELECT *` gradeable. A drill that asked for two named columns and
    got the whole table has returned the right data and the wrong *interface*,
    and this is the check that says so — usually required, because a query whose
    column list is wrong is wrong.

    `ordered` defaults to **true** here, the opposite of `result_matches`, and
    the asymmetry is real rather than an inconsistency. A column list is written
    by hand in the `SELECT` clause, so its order is always the author's choice
    and always reproducible; row order without `ORDER BY` is neither.
    """
    wanted = tuple(context.params.paths("columns"))
    ordered = context.params.flag("ordered", default=True)
    result = _result(context)
    shape = "in this order" if ordered else "in any order"

    if result is None:
        return CheckResult(
            passed=False,
            expected=f"columns {', '.join(wanted)} ({shape})",
            actual=_why_not(context),
        )

    found = result.columns
    passed = found == wanted if ordered else Counter(found) == Counter(wanted)
    return CheckResult(
        passed=passed,
        expected=f"columns {', '.join(wanted)} ({shape})",
        actual=f"columns {', '.join(found) if found else '<none>'}",
    )


def result_ordered_by(context: DrillContext) -> CheckResult:
    """`result_ordered_by {column, descending?}` — the rows are sorted by it.

    The assertion `result_matches {ordered: true}` cannot replace, and the
    distinction is the same one `is_ancestor` draws for git: this grades a
    *property* of the answer rather than its literal content. A top-N drill whose
    data changes still asserts "sorted by total, descending" unchanged, and more
    importantly the verdict names the property — "sorted by total descending" —
    rather than making a solver diff eight rows to discover that two are the
    wrong way round.

    **Compares textually, like everything else here**, which is a real limitation
    worth knowing: `10` sorts before `9` as text. So this is for ordering by a
    name, a date in ISO form, or a zero-padded number, and a drill ordering by a
    bare integer should assert `result_matches {ordered: true}` instead. Stated
    rather than fixed, because fixing it means the port reporting column types
    and the domain branching on them — a lot of machinery for a case the library
    does not have.
    """
    name = context.params.text("column")
    descending = context.params.flag("descending", default=False)
    direction = "descending" if descending else "ascending"
    result = _result(context)

    if result is None:
        return CheckResult(
            passed=False,
            expected=f"rows sorted by {name}, {direction}",
            actual=_why_not(context),
        )

    values = result.column(name)
    if values is None:
        return CheckResult(
            passed=False,
            expected=f"rows sorted by {name}, {direction}",
            actual=f"no column {name} in {', '.join(result.columns) or '<none>'}",
        )

    found = [as_text(value) for value in values]
    wanted = sorted(found, reverse=descending)
    return CheckResult(
        passed=found == wanted,
        expected=f"rows sorted by {name}, {direction}",
        actual=(
            f"{name} reads {', '.join(found) if found else '<no rows>'}"
            if found != wanted
            else f"{name} is sorted {direction}"
        ),
    )
