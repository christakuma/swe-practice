"""`name -> DrillFunction`, and the one place `not:` is applied to a drill check.

The drill family's registry, and a deliberate near-twin of
`domain/checks/registry.py` rather than a generalisation of it. The two were
briefly going to be one table with a family column, and that design is worth
recording because the reason it was rejected is the whole point of having two:

**a drill naming a git assertion has to be a build failure.** One registry
keyed by name alone would happily validate `assert: tree_equals` inside a
`sql_drill`, and the check would reach a dispatcher holding a `DrillQuery` where
it wanted a `RepoQuery` — an exercise that cannot grade, discovered at grading
time. Two registries make the vocabularies disjoint by construction, so
`adapters/content/schema.py` rejects the file instead, naming the assertion and
suggesting the nearest *drill* assertion to it.

What **is** shared is everything that is not a vocabulary: `CheckSpec`,
`CheckResult`, `CheckReport`, `Params`, `compare`, `matcher`, and the three jobs
`evaluate` does below. Those are the shape of an assertion, and the shape did not
change when the subject did — which is the better evidence that §6.3's "negation
is a modifier, not a set of paired opposites" was the right call than any
argument for it would be.

**Ten assertions, and §13's rule applies to every one.** Each is named by at
least one drill in `content/sql/`, and `tests/content/test_drills.py` asserts
that — the same standard that deleted `reflog_contains` and `command_count` in
Phase 11 rather than carrying them. An eleventh should not be added here before
the exercise that wants it exists.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from practice.domain.checks import registry as git_registry
from practice.domain.checks.evaluation import CheckSpecError, Params
from practice.domain.drills import craft, rows, tables
from practice.domain.drills.evaluation import DrillContext
from practice.domain.verdict import CheckReport

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.domain.drills.evaluation import DrillFunction
    from practice.domain.exercise import CheckSpec
    from practice.domain.ports import DrillQuery

__all__ = [
    "CRAFT_ASSERTIONS",
    "DRILL_ASSERTIONS",
    "DRILL_CHECKS",
    "STATE_ASSERTIONS",
    "evaluate",
    "is_registered",
    "misplaced_in_scenario",
    "other_family",
    "suggest",
]

#: What the answer returned.
_RESULT: Final[Mapping[str, DrillFunction]] = {
    "result_columns": rows.result_columns,
    "result_contains_row": rows.result_contains_row,
    "result_matches": rows.result_matches,
    "result_ordered_by": rows.result_ordered_by,
    "result_row_count": rows.result_row_count,
}

#: What the database was left holding — the core bet, for this kind.
_TABLES: Final[Mapping[str, DrillFunction]] = {
    "table_exists": tables.table_exists,
    "table_matches": tables.table_matches,
    "table_row_count": tables.table_row_count,
}

#: How the answer got there. Reads the solver's text and SQLite's plan rather
#: than any state, and advisory by convention for the reason `craft.py` gives.
_CRAFT: Final[Mapping[str, DrillFunction]] = {
    "query_plan_matches": craft.query_plan_matches,
    "sql_matches": craft.sql_matches,
}

#: Name to function: the whole drill vocabulary, grouped by what each family reads.
DRILL_CHECKS: Final[Mapping[str, DrillFunction]] = MappingProxyType(
    {**_RESULT, **_TABLES, **_CRAFT}
)

#: Every legal value of an `assert:` key inside a `drill:` block.
DRILL_ASSERTIONS: Final = frozenset(DRILL_CHECKS)

#: The craft family, by name. Exported so the content suite can hold the
#: convention — *craft is graded separately from correctness* (§4.4) — over the
#: library instead of over each author's memory.
CRAFT_ASSERTIONS: Final = frozenset(_CRAFT)

#: Everything that grades the answer or the database rather than the text.
STATE_ASSERTIONS: Final = DRILL_ASSERTIONS - CRAFT_ASSERTIONS


def is_registered(name: str) -> bool:
    """Whether `name` is a legal `assert:` value inside a `drill:` block."""
    return name in DRILL_ASSERTIONS


def evaluate(spec: CheckSpec, query: DrillQuery) -> CheckReport:
    """Run one drill check and report it in the author's words.

    The same three jobs `checks/registry.evaluate` does — negation, carrying the
    author's label, and turning a broken `with:` mapping into a failing report
    rather than a traceback — over a `DrillQuery`.

    **No `Attempt` parameter**, which is the one signature difference between the
    two dispatchers. `DrillContext` explains why: a drill has no command log for
    an assertion to read, because the whole of what the solver did is the file
    `DrillQuery.statements` already reports.
    """
    function = DRILL_CHECKS.get(spec.assertion)
    if function is None:  # pragma: no cover - the schema rejects the name first
        return CheckReport.from_spec(
            spec,
            passed=False,
            expected=f"the {spec.assertion} assertion",
            actual="<no function is registered for it>",
        )

    context = DrillContext(
        query=query, params=Params(assertion=spec.assertion, values=spec.params)
    )
    try:
        result = function(context)
    except CheckSpecError as exc:
        return CheckReport.from_spec(
            spec,
            passed=False,
            expected=f"a usable {spec.assertion} check",
            actual=f"<this exercise is misconfigured: {exc}>",
        )

    if spec.negated:
        result = result.negate()
    return CheckReport.from_spec(
        spec,
        passed=result.passed,
        expected=result.expected,
        actual=result.actual,
    )


def suggest(name: str, *, limit: int = 3) -> tuple[str, ...]:
    """Registered drill names close enough to `name` to be worth offering.

    The same trigram matching `checks/registry.suggest` uses, over the other
    vocabulary. **Shared by calling it**, not by copying it: this hands it the
    drill names, which is the one thing that differs, and the threshold and the
    algorithm stay in one place.
    """
    return git_registry.suggest_from(name, DRILL_ASSERTIONS, limit=limit)


def other_family(name: str) -> str | None:
    """The exercise kind this assertion *does* belong to, if it is not a drill's.

    **Here because the trigram suggester cannot do this job, which was a Phase 14
    finding rather than a prediction.** The plan was that an author writing
    `assert: tree_equals` inside a `drill:` block would be offered
    `table_matches` — very nearly the check they wanted. They are not: the
    `_SUGGESTION_THRESHOLD` in `checks/registry.py` is 0.2 and was *measured*
    against the git vocabulary, where a genuine typo scores 0.33 and up. A name
    from a different family is not a typo at all; `tree_equals` and
    `table_matches` share almost no trigrams, and the threshold correctly rejects
    it as noise. Lowering it to catch this case would make every unknown name
    produce three irrelevant suggestions, which is the failure that threshold
    exists to prevent.

    So the right answer is not a better guess, it is a different sentence. An
    assertion that is registered in the *other* family is a known fact rather
    than a similarity score, and saying *"`tree_equals` is a git_scenario
    assertion"* ends the problem where `did you mean ...?` would not have
    started to.

    Both directions live here rather than one in each registry, because
    `checks/registry.py` must not import this module — the dependency runs one
    way, and a cycle to produce an error message would be a poor trade.
    """
    if name in DRILL_ASSERTIONS:
        return None
    if git_registry.is_registered(name):
        return "git_scenario"
    return None


def misplaced_in_scenario(name: str) -> str | None:
    """The mirror of `other_family`, for a drill assertion written into a scenario.

    Lives here for the import-direction reason `other_family` gives, and is
    called from `adapters/content/schema.py` where both validators are.
    """
    if git_registry.is_registered(name):
        return None
    if name in DRILL_ASSERTIONS:
        return "sql_drill"
    return None
