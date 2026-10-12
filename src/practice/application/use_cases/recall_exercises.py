"""Which exercises have been done, and when. The read every list needed.

One query and one pure pass, handed to `application/tracks.py` for the reason
`SummariseProgress` hands its attempts to `application/progress.py`: the
reduction is where the decisions are, and a use case with the loop in it could
only be tested by building a repository.

**From the attempt log and not the card store**, which is the whole point of it.
A card says an exercise was *scheduled*, and scheduling is a button pressed
after grading; an exercise that was solved and then walked away from has no
card, and every surface that read cards went on offering it as new. The attempt
is the record that the work happened.

Keyed by exercise id, with no entry for an exercise never attempted, so a page
asks `records.get(exercise.id)` once per row and the absence is the answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.tracks import records_of

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.application.tracks import Record
    from practice.domain.ids import ExerciseId
    from practice.domain.ports import AttemptRepository

__all__ = ["RecallExercises"]


@dataclass(frozen=True, slots=True)
class RecallExercises:
    """Every exercise with a graded attempt, and what those attempts came to."""

    attempts: AttemptRepository

    def __call__(self) -> Mapping[ExerciseId, Record]:
        """No content repository: an exercise that has left the library was
        still done, and whether to show it is the caller's question -- a page
        listing the library never asks about it, and nothing here needs to know.
        """
        return records_of(self.attempts.completed())
