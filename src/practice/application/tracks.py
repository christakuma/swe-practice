"""What the history says about each exercise, and where that leaves a track.

A view model, like `application/progress.py` and for the same reasons: nothing
here asks a port anything. It is handed the graded attempts, the library and a
track that a use case has already fetched and decides what they add up to, which
makes it pure, puts it inside the coverage gate, and keeps the arithmetic out of
a route.

**Why this exists at all, when every attempt was already being stored.** The
history was complete and the product could not be asked about it. `/progress`
lists attempts and rates tags; the due queue lists cards. Neither answers the
first question somebody has about a list of a hundred and fifteen exercises —
*which of these have I done, and when* — because both are organised around
something other than the exercise. From the outside that is indistinguishable
from a tool that forgot: the browse page looked the same on the fortieth visit
as on the first, and an exercise solved but never given a schedule grade was
still offered as **new**. `Record` is the per-exercise reading that was missing,
and it is derived from attempts rather than cards for exactly that reason — a
card exists only if a button was pressed, and an attempt exists because the
work was done.

**Done means passed at least once, and stays meant.** A later failed attempt
does not un-do an exercise: it happened, `last_attempted_at` shows it, and the
scheduler is the part of the product whose job is to notice forgetting. A track
is a route, and a route whose finished steps could reopen behind you is one
nobody can finish.

**`next_up` and `after` are two questions, and the second is the Next button.**
`next_up` is the first unfinished step from the top: what *Continue* means on a
track somebody is coming back to. `after` starts beyond a given step and wraps,
which is what somebody who has just finished — or just failed — that step is
asking for. Returning the first unfinished step to a solver who failed step
nine and pressed Next would hand them step nine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from datetime import datetime

    from practice.domain.attempt import Attempt
    from practice.domain.exercise import Exercise
    from practice.domain.ids import ExerciseId
    from practice.domain.track import Track

__all__ = [
    "NextStep",
    "Record",
    "Step",
    "TrackProgress",
    "choose",
    "follow",
    "records_of",
]


@dataclass(frozen=True, slots=True)
class Record:
    """Every graded attempt at one exercise, reduced to what a list can show.

    Only exists for an exercise that has been attempted, so `attempts` is never
    zero and `last_attempted_at` is never missing — the absence of a record *is*
    the not-yet-attempted state, and a row with a zero in it would be a second
    way to say the same thing.
    """

    attempts: int
    passes: int
    last_attempted_at: datetime
    last_passed_at: datetime | None = None

    @property
    def is_done(self) -> bool:
        """Passed at least once. See the module docstring for why once is enough."""
        return self.last_passed_at is not None


@dataclass(frozen=True, slots=True)
class Step:
    """One exercise on a track, with its place and what the history says of it.

    `number` counts from one, because it is only ever shown to a person, and it
    is the exercise's place on the *track* rather than in this tuple — so step
    twelve is still called twelve if step three has left the library.
    """

    number: int
    exercise: Exercise
    record: Record | None = None

    @property
    def is_done(self) -> bool:
        return self.record is not None and self.record.is_done


@dataclass(frozen=True, slots=True)
class TrackProgress:
    """A track, walked: every step in order and how far along it somebody is."""

    track: Track
    steps: tuple[Step, ...]

    @property
    def total(self) -> int:
        return len(self.steps)

    @property
    def done(self) -> int:
        return sum(1 for step in self.steps if step.is_done)

    @property
    def is_complete(self) -> bool:
        """Every step passed. False for a track with no steps left to show,
        which has not been finished so much as emptied.
        """
        return bool(self.steps) and self.done == self.total

    @property
    def next_up(self) -> Step | None:
        """The first unfinished step from the top, or `None` when there is none."""
        return next((step for step in self.steps if not step.is_done), None)

    def after(self, exercise_id: ExerciseId) -> Step | None:
        """The first unfinished step *beyond* this exercise, wrapping to the top.

        `Track.after` decides the order searched and this decides what counts
        as a hit. `None` means nothing else on the track is unfinished — which
        is not quite `is_complete`, because the exercise asked about is never a
        candidate for its own successor.
        """
        steps = {step.exercise.id: step for step in self.steps}
        for candidate in self.track.after(exercise_id):
            step = steps.get(candidate)
            if step is not None and not step.is_done:
                return step
        return None


@dataclass(frozen=True, slots=True)
class NextStep:
    """Where to go from one exercise: the track being followed and the step.

    The progress comes along because a button that says *Next* reads better with
    *12 of 75* beside it, and because `step` being `None` needs the track to say
    which one has just run out.
    """

    progress: TrackProgress
    step: Step | None


def records_of(attempts: Iterable[Attempt]) -> dict[ExerciseId, Record]:
    """One record per exercise that has a graded attempt.

    **An attempt without both a verdict and an end is skipped**, the same
    narrowing `progress.summarise` makes and for the same reason: the fields are
    optional on the aggregate, and a reading that trusted its caller to have
    filtered would be one import away from counting an open attempt as a
    failure.
    """
    found: dict[ExerciseId, Record] = {}
    for attempt in attempts:
        if attempt.finished_at is None or attempt.verdict is None:
            continue
        ended = attempt.finished_at
        passed = attempt.verdict.passed
        seen = found.get(attempt.exercise_id)
        last_passed = seen.last_passed_at if seen is not None else None
        if passed and (last_passed is None or ended > last_passed):
            last_passed = ended
        found[attempt.exercise_id] = Record(
            attempts=(seen.attempts if seen is not None else 0) + 1,
            passes=(seen.passes if seen is not None else 0) + (1 if passed else 0),
            last_attempted_at=(
                ended
                if seen is None or ended > seen.last_attempted_at
                else seen.last_attempted_at
            ),
            last_passed_at=last_passed,
        )
    return found


def follow(
    track: Track,
    *,
    exercises: Mapping[ExerciseId, Exercise],
    records: Mapping[ExerciseId, Record],
) -> TrackProgress:
    """Walk a track against a library and a history.

    A step whose exercise the library no longer holds is left out rather than
    raised about. The content repository resolves a track against its own
    exercises, so this is a branch only a library edited under a running server
    reaches — and the honest thing to show then is a track one step short.
    """
    return TrackProgress(
        track=track,
        steps=tuple(
            Step(
                number=index + 1,
                exercise=exercises[exercise_id],
                record=records.get(exercise_id),
            )
            for index, exercise_id in enumerate(track.exercises)
            if exercise_id in exercises
        ),
    )


def choose(tracks: Sequence[Track], name: str | None) -> Track | None:
    """The track somebody is on: the one they named, or else the first.

    **The first track is the default**, which is `ContentRepository.list_tracks`'s
    documented contract rather than a choice made here. A name that matches
    nothing falls back to it as well, instead of being refused: the name arrives
    in a query string and a form field, and a stale link to a track that has
    been renamed should still have a Next button on it.

    `None` only for a library that declares no tracks at all.
    """
    for track in tracks:
        if track.name == name:
            return track
    return tracks[0] if tracks else None
