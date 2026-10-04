"""Scheduling: when an exercise comes back, and how hard it was.

Three pure modules behind one port and one plain function. `sm2.py` and
`fsrs.py` each move a card; `suggestion.py` decides which grade to move it with.
The split is because only the first two are `Scheduler`s — the suggestion is a
reading of an attempt that any scheduler would want, and burying it behind the
port would make a second algorithm re-implement a rule that has nothing to do
with intervals.

**That prediction is now a result rather than a claim.** The sentence above said
"a second algorithm (FSRS is the one §4.6 names)" from Phase 9; Phase 13 wrote
it, and `suggestion.py` did not change by a character. The two schedulers share
this package, the `Grade` enum, the four properties in
`tests/unit/domain/scheduling/test_scheduler_conformance.py` — and nothing else.

Both live in `domain/` rather than `application/`, which is the line PLAN.md §3
draws and this is on the near side of it: an interval and a grade are things the
product can be *right or wrong about*, graded by property tests, with no port in
sight. The lane numbers in `application/graph.py` are the contrast — those are
what a panel looks like.
"""

from practice.domain.scheduling.fsrs import DEFAULT_WEIGHTS, FsrsScheduler
from practice.domain.scheduling.sm2 import Sm2Scheduler
from practice.domain.scheduling.suggestion import GradeSuggestion, suggest_grade

__all__ = [
    "DEFAULT_WEIGHTS",
    "FsrsScheduler",
    "GradeSuggestion",
    "Sm2Scheduler",
    "suggest_grade",
]
