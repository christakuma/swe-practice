"""Where to go after this exercise. The answer behind the Next button.

Before this, a finished attempt ended in a link back to the queue — and only
once a schedule grade had been pressed. Working through a list meant: grade,
back, find your place, start. This is the step that removes the middle two.

**It follows a track rather than the due queue**, and that was the alternative
considered. The queue is the tool's answer to *what should I practise today*,
so the head of it looks like the natural next thing. It is not, for a reason
that only shows up in use: an exercise leaves the queue when it is *scheduled*,
not when it is solved, so a solver moving quickly and skipping the grade buttons
would be handed back the exercises they had just passed. A track asks the
attempt history, which changes the moment the work is graded.

**Which track is the caller's to say and this use case's to default.** The web
app carries the name from the page an attempt was started on. When there is
none — an attempt started from Browse, or resumed from the dashboard — the
first declared track is followed, which `application/tracks.choose` documents
and `content/tracks.yaml` arranges to be the whole library in curriculum order.

**It reads; it does not start anything.** The page posts to the same
`/attempt` every Start button does, so there is one way an attempt begins and
this is not a second one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.tracks import NextStep, choose, follow, records_of

if TYPE_CHECKING:
    from practice.domain.ids import ExerciseId
    from practice.domain.ports import AttemptRepository, ContentRepository

__all__ = ["NextExercise"]


@dataclass(frozen=True, slots=True)
class NextExercise:
    """The first unfinished step beyond an exercise, on the track being followed."""

    content: ContentRepository
    attempts: AttemptRepository

    def __call__(
        self, exercise_id: ExerciseId, track: str | None = None
    ) -> NextStep | None:
        """`None` only when the library declares no tracks, so there is no
        route to be on. A track with nothing left unfinished is an answer, not
        an absence: it comes back as a `NextStep` whose `step` is `None`, and
        the page says the track is finished.

        `exercise_id` need not be on the track. Somebody who wandered off to an
        exercise from Browse and pressed Next is sent to the first unfinished
        step from the top, which is where they were.
        """
        chosen = choose(self.content.list_tracks(), track)
        if chosen is None:
            return None
        progress = follow(
            chosen,
            exercises={
                exercise.id: exercise for exercise in self.content.list_exercises()
            },
            records=records_of(self.attempts.completed()),
        )
        return NextStep(progress=progress, step=progress.after(exercise_id))
