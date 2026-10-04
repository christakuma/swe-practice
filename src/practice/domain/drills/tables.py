"""What the database was left holding. Three of the ten drill assertions.

**This is the family that makes a SQL drill the same kind of thing as a git
scenario.** The project's core bet is to grade the end state rather than the
answer text (PLAN.md §1), and for a `SELECT` that bet is nearly free — the rows
*are* the end state. It only becomes a claim worth testing for the statements
that change something: an `UPDATE` that should touch three rows and not thirty,
a `DELETE` with a `WHERE` the solver forgot, an `INSERT ... ON CONFLICT`. None of
those return anything at all, so `rows.py` cannot see them; what tells a right
answer from a wrong one is the table afterwards.

That is the direct analogue of §6.6's central finding about git — that
`content-restored` passes for a revert, a `reset --hard` and a forgotten push
alike, so the discriminating assertion is almost always about where a ref
points. Here the discriminating assertion is almost always about the rows a
table still has, and a drill that only checks what came back is a drill that
would pass `DELETE FROM orders`.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from practice.domain.checks.evaluation import CheckResult, compare
from practice.domain.drills.evaluation import (
    as_rows,
    describe_rows,
    expected_rows,
    table_of,
)

if TYPE_CHECKING:
    from practice.domain.drills.evaluation import DrillContext

__all__ = ["table_exists", "table_matches", "table_row_count"]

#: What a report says about a table that is not in the database. A table the
#: answer dropped and a table the drill misnamed look identical from here, which
#: is why the message says what *is* there.
_GONE = "<no such table>"


def table_matches(context: DrillContext) -> CheckResult:
    """`table_matches {table, rows, ordered?}` — the table holds exactly these rows.

    The end-state assertion. Rows come back in `rowid` order from the port, so
    `ordered: true` is meaningful and means *insertion order*, which is what an
    `INSERT` drill wants to assert and what an `UPDATE` drill wants to ignore.
    Multiset by default, for the same reason `result_matches` is.

    **Compares the whole table, not a subset**, and that is the point rather than
    a convenience gap. An `UPDATE ... WHERE` graded by "the three rows I expected
    changed" passes an answer that changed those three *and* thirty others; only
    comparing everything catches it. A drill over a table too wide to write out
    should assert `table_row_count` plus `result_matches` over a `SELECT` of the
    columns it cares about.
    """
    wanted = expected_rows(context.params)
    ordered = context.params.flag("ordered", default=False)
    name = context.params.text("table")
    table = table_of(context)
    shape = "in this order" if ordered else "in any order"
    expected = f"{name} holding {describe_rows(wanted)} ({shape})"

    if table is None:
        return CheckResult(passed=False, expected=expected, actual=_GONE)

    found = as_rows(table)
    passed = found == wanted if ordered else Counter(found) == Counter(wanted)
    return CheckResult(
        passed=passed, expected=expected, actual=f"{name} holds {describe_rows(found)}"
    )


def table_row_count(context: DrillContext) -> CheckResult:
    """`table_row_count {table, equals|at_least|at_most}` — how many rows survived.

    The cheapest check in the vocabulary and the one most worth adding to a
    destructive drill. A `DELETE` whose `WHERE` matched nothing and a `DELETE`
    that emptied the table are both "no rows returned"; this is what separates
    them, and it reads in a verdict as the single number a solver can act on.
    """
    operator, wanted = context.params.comparison()
    name = context.params.text("table")
    table = table_of(context)
    phrase = operator.replace("_", " ")
    expected = f"{name} holding {phrase} {wanted} row(s)"

    if table is None:
        return CheckResult(passed=False, expected=expected, actual=_GONE)
    return CheckResult(
        passed=compare(operator, table.row_count, wanted),
        expected=expected,
        actual=f"{name} holds {table.row_count} row(s)",
    )


def table_exists(context: DrillContext) -> CheckResult:
    """`table_exists {table}` — there is a table or view by this name.

    For the drills whose answer is a `CREATE`, and — with `not: true` — for the
    drills whose answer is a `DROP`. Views count, deliberately: a drill that asks
    for a reusable query is satisfied by either, and `tables()` reporting both is
    what lets the author decide rather than the engine.

    The `actual` lists what is there, which is the whole reason this is not just
    a membership test: the failure is nearly always a typo or a plural, and
    seeing `orders, customers, order_totals` next to a missing `order_total`
    ends the problem at the message.
    """
    name = context.params.text("table")
    tables = context.query.tables()
    return CheckResult(
        passed=name in tables,
        expected=f"a table or view named {name}",
        actual=", ".join(sorted(tables)) if tables else "<no tables at all>",
    )
