"""What a drill assertion is given, and how a value compares to an author's word.

The drill family's counterpart to `domain/checks/evaluation.py`, and it is
deliberately much shorter than that module, because it **reuses** rather than
restates. `CheckResult`, `CheckSpecError`, `Params`, `compare` and `matcher` are
imported from there and not copied: they are about the *shape* of an assertion
and the *shape* of an author's `with:` mapping, neither of which has anything to
do with git. What stayed behind is the genuinely git-specific half — `resolve`,
`alias_name` and `describe`, which are about revisions.

Two decisions are this module's own.

**Comparison is textual, and the rule is written down here rather than in the
port.** `ResultSet` holds what SQLite handed back: `int`, `float`, `str`,
`bytes`, `None`. An author writes `rows: [[alice, 2]]` in YAML, where `2` may
arrive as an `int` and `alice` as a `str`. Comparing those as Python objects
would make `2 == "2"` false and fail a correct answer over a YAML typing
accident, so both sides go through `as_text` and the comparison is on the
result. The alternative — coercing the author's value to the column's type —
needs a type the port does not report and would silently compare `0` to
`"false"`.

That makes the port honest and the policy visible: *how a NULL compares* is a
grading decision, and grading decisions belong in the domain where they can be
unit-tested, not in a driver.

**Floats are formatted, not rounded, and drills are expected to `ROUND` in SQL.**
`as_text` renders a float with `%g`, so `2.0` is `2` and
`2.3333333333333335` is `2.33333`. That is enough for a drill over tens of rows
and no help at all for an average, which is the point: a drill whose answer is
an average should ask for `ROUND(AVG(total), 2)`, because controlling the
precision of what you return *is* the lesson. A grader that quietly rounded to
match would teach the opposite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from practice.domain.checks.evaluation import CheckSpecError

if TYPE_CHECKING:
    from collections.abc import Callable

    from practice.domain.checks.evaluation import CheckResult, Params
    from practice.domain.exercise import ParamValue
    from practice.domain.ports import DrillQuery, ResultSet, Scalar

__all__ = [
    "NO_RESULT",
    "NULL",
    "DrillContext",
    "DrillFunction",
    "as_row",
    "as_rows",
    "as_text",
    "describe_rows",
    "expected_rows",
    "single_row",
    "table_of",
]

#: What a report says about a `NULL`. One spelling everywhere, and the spelling
#: an author writes in YAML to mean it — `rows: [[alice, NULL]]`. Upper case
#: because that is how SQL spells it and a drill is teaching SQL.
NULL: Final = "NULL"

#: What a report says when the answer returned no rows at all. Distinct from an
#: empty result set, which is a real answer that happens to have no rows:
#: `result_row_count {equals: 0}` passes against one and fails against this.
NO_RESULT: Final = "<the answer returned no rows>"

#: Significant digits `as_text` renders a float to — see the module docstring on
#: why this is a formatting rule and not a rounding one.
_FLOAT_FORMAT: Final = "g"


@dataclass(frozen=True, slots=True)
class DrillContext:
    """Everything a drill assertion may read.

    `query` for the database and the answer, `params` for the author's `with:`
    mapping. **Two things, where `CheckContext` has three**, and the missing one
    is the `Attempt`.

    That is not an oversight and it is the most interesting difference between
    the two families. A git scenario's `command_used` reads the attempt's event
    log because the *sequence of commands* is part of what is being taught, and
    the repository cannot hold it. A drill has no command console: the whole of
    what the solver did is one file, and `DrillQuery.statements` already reports
    it. An assertion here that took the attempt would be reaching for a history
    that does not exist.
    """

    query: DrillQuery
    params: Params


#: Every drill assertion has this shape, which is what lets the registry be a
#: table — the same contract `CheckFunction` states for the git family, over a
#: different context.
type DrillFunction = Callable[[DrillContext], CheckResult]


def as_text(value: Scalar) -> str:
    """One cell, as the thing an author's YAML is compared against.

    `None` becomes `NULL`, a `float` is formatted rather than rounded, `bytes`
    becomes a placeholder, and everything else is `str`. A blob is a placeholder
    rather than a decode attempt because no drill in the library stores one and
    guessing an encoding to put bytes in a verdict panel would be inventing
    content.
    """
    if value is None:
        return NULL
    if isinstance(value, bytes):
        return "<blob>"
    if isinstance(value, bool):
        # Before `int`, because `bool` is one. SQLite never returns a `bool`, but
        # a fake and an author's YAML both can, and `True` must not read as
        # `True` where the column holds `1`.
        return "1" if value else "0"
    if isinstance(value, float):
        return format(value, _FLOAT_FORMAT)
    return str(value)


def as_row(row: tuple[Scalar, ...]) -> tuple[str, ...]:
    """One row, cell by cell."""
    return tuple(as_text(cell) for cell in row)


def as_rows(result: ResultSet) -> tuple[tuple[str, ...], ...]:
    """Every row of a result set, in the order it came back."""
    return tuple(as_row(row) for row in result.rows)


def expected_rows(params: Params, name: str = "rows") -> tuple[tuple[str, ...], ...]:
    """The author's literal rows, out of the `with:` mapping and normalised.

    Accepts a list of rows, and a single flat row as a list of one — the same
    kindness `Params.paths` extends for the same reason: YAML makes
    `rows: [alice, 2]` and `rows: [[alice, 2]]` look equally correct, and a
    one-row expectation is the common case.

    **Refuses ragged rows**, which is the authoring mistake this is really here
    for. Rows of different widths can never all match a result set, so at least
    one check is dead on arrival — the vacuous-check failure §5.4 is about,
    arriving as a shape error instead of a missing one.
    """
    value = params.values.get(name)
    if value is None:
        raise CheckSpecError(f"{params.assertion}: missing required parameter {name!r}")
    if not isinstance(value, tuple) or not value:
        raise CheckSpecError(
            f"{params.assertion}: {name!r} must be a non-empty list of rows, "
            f"got {value!r}"
        )

    rows = value if any(isinstance(item, tuple) for item in value) else (value,)
    normalised = []
    for row in rows:
        if not isinstance(row, tuple) or not row:
            raise CheckSpecError(
                f"{params.assertion}: every row in {name!r} must be a non-empty "
                f"list of values, got {row!r}"
            )
        normalised.append(tuple(_cell(params, name, cell) for cell in row))

    widths = {len(row) for row in normalised}
    if len(widths) > 1:
        raise CheckSpecError(
            f"{params.assertion}: every row in {name!r} must have the same number "
            f"of values, got widths {sorted(widths)}"
        )
    return tuple(normalised)


def _cell(params: Params, name: str, cell: ParamValue) -> str:
    """One value out of an author's row, refusing a nested list.

    `ParamValue` is recursive, so YAML that nests one level too deep —
    `rows: [[[alice, 2]]]` — parses cleanly and would otherwise be compared as
    the string `('alice', 2)`, which can never match anything. A check that can
    never pass is the vacuous-check failure §5.4 is about, pointing the other
    way.
    """
    if isinstance(cell, tuple):
        raise CheckSpecError(
            f"{params.assertion}: {name!r} holds a nested list where a value "
            f"belongs: {cell!r}"
        )
    return as_text(cell)


def single_row(params: Params, name: str = "row") -> tuple[str, ...]:
    """Exactly one row out of the `with:` mapping, for `result_contains_row`.

    Refuses a list of rows rather than taking the first, which is the whole
    reason it is not just `expected_rows(...)[0]`. An author who wrote two rows
    under `row:` meant two assertions, and silently grading one of them is the
    vacuous-check failure §5.4 is about — a check that passes while testing less
    than it says.
    """
    rows = expected_rows(params, name)
    if len(rows) > 1:
        raise CheckSpecError(
            f"{params.assertion}: {name!r} takes one row, got {len(rows)}; "
            f"write one check per row"
        )
    return rows[0]


def table_of(context: DrillContext, name: str = "table") -> ResultSet | None:
    """The table an assertion's `table:` parameter names, or `None` if it is gone.

    One accessor rather than three copies of `params.text` followed by
    `query.table`, because the `None` case is the one that matters and it has to
    be reported identically by every assertion that can hit it: a drill whose
    answer dropped the table it was supposed to update must not read as a
    different failure from one that renamed it.
    """
    return context.query.table(context.params.text(name))


def describe_rows(rows: tuple[tuple[str, ...], ...], *, limit: int = 4) -> str:
    """Rows as one line of a verdict, truncated so a panel stays readable.

    A drill's expected answer is a handful of rows by design, so the limit is
    rarely reached — but a *wrong* answer can return the whole table, and a
    verdict that pastes two hundred rows into the panel is a verdict nobody
    reads. The count is always stated, so the truncation never hides the thing
    that is actually wrong.
    """
    if not rows:
        return "no rows"
    shown = " | ".join(", ".join(row) for row in rows[:limit])
    if len(rows) > limit:
        return f"{len(rows)} rows: {shown} | ..."
    return f"{len(rows)} rows: {shown}"
