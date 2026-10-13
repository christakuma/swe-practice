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

        **A variant stands where its base stands.** It is on no track, by
        construction (ADR 0028), so asked about literally it is always the
        wanderer above -- and somebody who took the twist on step forty and
        pressed Next was handed step three. They have not wandered: the track
        page is where they chose it. So the search starts after the base.

        And it ends *on* the base, which is the one place a variant differs
        from the exercise it stands in for. `TrackProgress.after` never offers
        an exercise as its own successor, rightly -- but the twist is not the
        base, and a solver who took it on the last unfinished step would
        otherwise be told there was nothing left on a track with a step still
        open.
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
        finished = self.content.get(exercise_id)
        if finished is None or finished.variant is None:
            return NextStep(progress=progress, step=progress.after(exercise_id))

        base = finished.variant.of
        step = progress.after(base) or next(
            (
                found
                for found in progress.steps
                if found.exercise.id == base and not found.is_done
            ),
            None,
        )
        return NextStep(progress=progress, step=step)
