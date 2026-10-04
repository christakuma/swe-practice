"""How the answer got there. Two of the ten drill assertions.

The drill family's counterpart to `checks/process.py`, and it exists for the same
reason that one does: some lessons are about *how*, and no end state can hold
them. `process.py` reads the attempt's command log because a force-push is
invisible in a repository that ended up correct; these two read the answer's text
and its query plan because a correlated subquery over ten thousand rows is
invisible in a result set that is right.

**Advisory by convention, and the convention is load-bearing.** Both of these
grade craft rather than correctness, and §4.4 is explicit that the two are graded
separately: *you achieved the goal, but the way you did it has consequences*. A
*required* check over the text of an answer would also be exactly the string
matching ADR 0003 rejected — "did you type the word JOIN" is not a question
about whether the answer is right, and an exercise that failed a correct query
for spelling it differently would be the tool teaching superstition.

Nothing enforces the convention, which is the same position `command_used` is in.
`registry.py` groups both families under a name — `CRAFT_ASSERTIONS` — so that
the content suite can assert the rule over the library rather than trusting
each author to remember it.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from practice.domain.checks.evaluation import CheckResult, matcher

if TYPE_CHECKING:
    from practice.domain.drills.evaluation import DrillContext

__all__ = ["query_plan_matches", "sql_matches"]

#: How much of a matched line a verdict quotes. A query plan line is short; a
#: statement can be the whole answer, and a panel that pasted forty lines of SQL
#: into the `actual` field would bury the thing it is reporting.
_QUOTE_LIMIT = 90


def sql_matches(context: DrillContext) -> CheckResult:
    """`sql_matches {pattern}` — some statement in the answer matches it.

    The *technique* assertion: `window function`, `with recursive`, `left join`.
    Unanchored and case-insensitive, because SQL keywords are written both ways
    by reasonable people and an author who wrote `JOIN` did not mean to fail
    `join`.

    Most useful negated. `not: true` with a pattern of `select\\s+\\*` is how a
    drill says *name your columns*, and with `(?s)\\(\\s*select` how it says
    *that subquery should have been a join* — both of which are advisory notes on
    an answer that already returned the right rows.

    Reports **which** statement matched rather than just that one did, because
    the negated form is the common one and "nothing matched" is useless feedback
    next to the line that did.
    """
    pattern = _insensitive(context)
    statements = context.query.statements()
    for statement in statements:
        found = pattern.search(statement)
        if found is not None:
            return CheckResult(
                passed=True,
                expected=f"SQL matching /{pattern.pattern}/",
                actual=f"matched {_quote(statement)}",
            )
    return CheckResult(
        passed=False,
        expected=f"SQL matching /{pattern.pattern}/",
        actual=(
            f"no match in {len(statements)} statement(s)"
            if statements
            else "<no SQL was submitted>"
        ),
    )


def query_plan_matches(context: DrillContext) -> CheckResult:
    """`query_plan_matches {pattern}` — a line of `EXPLAIN QUERY PLAN` matches it.

    **The assertion this kind exists for**, and the one no amount of comparing
    rows can replace. Two answers returning identical rows can differ by a factor
    of a thousand in work done, and SQLite says which is which in a form stable
    enough to assert on: `SEARCH orders USING INDEX idx_orders_customer` where
    the slow answer says `SCAN orders`.

    So `not: true` with a pattern of `\\bSCAN\\b` is a drill saying *that index
    exists; use it* — a `PASS_WITH_ADVISORIES` on a correct answer, which is
    §4.4's mechanism carrying the single most transferable thing in the SQL
    track.

    Case-sensitive, unlike `sql_matches`, and the asymmetry is deliberate: the
    plan is SQLite's output rather than the solver's input, `SCAN` and `SEARCH`
    are spelled by the engine, and a case-insensitive `\\bscan\\b` would also
    match a table called `scans`.
    """
    pattern = matcher(context.params)
    lines = context.query.plan()
    for line in lines:
        if pattern.search(line) is not None:
            return CheckResult(
                passed=True,
                expected=f"a query plan line matching /{pattern.pattern}/",
                actual=f"matched {_quote(line)}",
            )
    return CheckResult(
        passed=False,
        expected=f"a query plan line matching /{pattern.pattern}/",
        actual=(
            " / ".join(_quote(line) for line in lines)
            if lines
            else "<there was no query plan>"
        ),
    )


def _insensitive(context: DrillContext) -> re.Pattern[str]:
    """The author's pattern, recompiled to ignore case.

    Through `matcher` rather than `re.compile` on the raw parameter, so a pattern
    that will not compile is still the `CheckSpecError` the dispatcher turns into
    a readable authoring failure — the flag is the only thing added.
    """
    return re.compile(matcher(context.params).pattern, re.IGNORECASE)


def _quote(text: str) -> str:
    """One line of SQL or plan output, flattened and capped for a verdict panel."""
    flat = " ".join(text.split())
    if len(flat) <= _QUOTE_LIMIT:
        return repr(flat)
    return repr(f"{flat[:_QUOTE_LIMIT]}...")
