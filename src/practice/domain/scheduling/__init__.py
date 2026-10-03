"""Scheduling: when an exercise comes back, and how hard it was.

Two pure modules behind one port and one plain function. `sm2.py` moves a card;
`suggestion.py` decides which grade to move it with. They are split because only
the first is a `Scheduler` — the suggestion is a reading of an attempt that any
scheduler would want, and burying it behind the port would make a second
algorithm (FSRS is the one §4.6 names) re-implement a rule that has nothing to do
with intervals.

Both live in `domain/` rather than `application/`, which is the line PLAN.md §3
draws and this is on the near side of it: an interval and a grade are things the
product can be *right or wrong about*, graded by property tests, with no port in
sight. The lane numbers in `application/graph.py` are the contrast — those are
what a panel looks like.
"""

from practice.domain.scheduling.sm2 import Sm2Scheduler
from practice.domain.scheduling.suggestion import GradeSuggestion, suggest_grade

__all__ = ["GradeSuggestion", "Sm2Scheduler", "suggest_grade"]
