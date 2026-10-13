"""Everything the dashboard and `/progress` say about how it is going.

Three reads and one pure pass: the graded attempts, the library they were at, and
the cards that hold the lapse counts, handed to `application/progress.py`. The
arithmetic is there rather than here for the reason `InspectRepository` keeps the
graph in `application/graph.py` — a use case's job is to gather what a pure
function needs, and a use case with a loop in it is a use case that can only be
tested by building a repository.

**One summary for both pages, not one per page.** The dashboard wants the streak
and three weak tags; `/progress` wants the table, the history and the window.
Splitting them would mean two passes over the same attempts, and the first time
the two disagreed — a streak on one page and a different streak on the other —
nothing would say which was right. `Progress` is cheap to over-answer: a page
reads the fields it needs and ignores the rest.

**The library is fetched whole rather than per attempt.** Mastery is a join from
every attempt to its exercise's tags, and the alternative is one `content.get`
per attempt, which is the shape that gets slower exactly as the history gets
interesting.

**Then the exercises the listing leaves out, one lookup each.** A variant is
never listed (ADR 0028) and is attempted like anything else, so a library read
through `list_exercises` alone had no tags for it: three failures at a twist
moved the totals and the streak and left the tag they were failures *at*
exactly where it was. `ReviewQueue` met the same gap and closes it the same
way. It is one `get` per attempted exercise the listing did not hold, not per
attempt -- bounded by the variants somebody has tried, which is the shape the
paragraph above is avoiding and not the one this is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.progress import WINDOW_DAYS, summarise

if TYPE_CHECKING:
    from practice.application.progress import Progress
    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        ReviewRepository,
    )

__all__ = ["SummariseProgress"]


@dataclass(frozen=True, slots=True)
class SummariseProgress:
    """How the practice is going, from the attempt log and the card store."""

    content: ContentRepository
    attempts: AttemptRepository
    reviews: ReviewRepository
    clock: Clock

    def __call__(self, window_days: int = WINDOW_DAYS) -> Progress:
        """No provisioner: none of this is a question about a workspace.

        `window_days` is a parameter rather than a constant read here so a test
        can ask for a window it can write out, and so a future "last 90 days"
        control is a query string and not a second use case. The default is the
        one the pages use.
        """
        attempts = self.attempts.completed()
        exercises = {
            exercise.id: exercise for exercise in self.content.list_exercises()
        }
        attempted = {attempt.exercise_id for attempt in attempts}
        for unlisted in attempted - exercises.keys():
            found = self.content.get(unlisted)
            # Still `None` for an exercise that has left the library, which
            # `summarise` counts and cannot tag.
            if found is not None:
                exercises[unlisted] = found
        return summarise(
            attempts=attempts,
            exercises=exercises,
            cards=self.reviews.cards(),
            today=self.clock.today(),
            window_days=window_days,
        )
