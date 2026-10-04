"""The SQL drill check engine: ten pure assertions over a `DrillQuery`.

The third exercise kind's grading vocabulary (PLAN.md §11, Phase 14), and a
sibling of `domain/checks/` rather than an extension of it. The division of
labour between the two packages, which is the thing to understand before adding
anything here:

* `domain/checks/` grades a **repository**, through `RepoQuery`. Twenty
  assertions, and `CheckContext` carries the attempt because a git lesson can be
  about the sequence of commands.
* `domain/drills/` grades a **database and a result set**, through `DrillQuery`.
  Ten assertions, and `DrillContext` carries no attempt because a drill is one
  file and there is no sequence.

They share what is not a vocabulary — `CheckSpec`, `CheckResult`, `CheckReport`,
`Params`, `compare`, `matcher`, `suggest_from` — and keep their assertion tables
disjoint on purpose, so that a drill naming `tree_equals` is rejected by the
schema rather than discovered at grading time. `registry.py` has the argument.

Three families, by what each reads:

* `rows.py` — what the answer returned. Five assertions.
* `tables.py` — what the database was left holding. Three, and the ones that
  make this kind an instance of the core bet rather than a result-set differ.
* `craft.py` — how the answer got there: its text, and SQLite's query plan.
  Two, advisory by convention (§4.4).
"""

from practice.domain.drills.evaluation import (
    DrillContext,
    DrillFunction,
    as_text,
)
from practice.domain.drills.registry import (
    CRAFT_ASSERTIONS,
    DRILL_ASSERTIONS,
    DRILL_CHECKS,
    STATE_ASSERTIONS,
    evaluate,
    is_registered,
    misplaced_in_scenario,
    other_family,
    suggest,
)

__all__ = [
    "CRAFT_ASSERTIONS",
    "DRILL_ASSERTIONS",
    "DRILL_CHECKS",
    "STATE_ASSERTIONS",
    "DrillContext",
    "DrillFunction",
    "as_text",
    "evaluate",
    "is_registered",
    "misplaced_in_scenario",
    "other_family",
    "suggest",
]
