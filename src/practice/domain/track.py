"""A track: a named route through the library that somebody can follow.

*The Blind 75*, *Git scenarios* — a list with a first exercise, a next one and
an end, which is the thing a browse page and a due queue between them never
offered. Browse is the whole library with no position in it, and the queue is
what the scheduler wants today; neither can answer *where was I*.

**It is not the curriculum, and the difference is the reason both exist.**
`content/curriculum.yaml` is one total order over every exercise, each named
exactly once, interleaved on purpose so that a solver working down it meets git
and katas alternately (ADR 0014). A track is a *selection* with an order of its
own, and an exercise can sit on several: Two Sum is the first step of the Blind
75 and the second of the whole library. A structure that names every exercise
exactly once cannot say that, which is why this is a second manifest rather
than a second key on the first (ADR 0025).

The curriculum's own groups are also called tracks, in `curriculum.yaml` and in
`adapters/content/curriculum.py`, and that name was taken first. They are
sections of the one order and nobody follows one; this is the type the rest of
the system means by the word.

**Resolved, not declared.** `content/tracks.yaml` may say *follow the
curriculum* instead of listing ids, and by the time one of these exists that has
been turned into the ids it means. So every reader — a use case, a page, a test
— is handed an ordered tuple and never has to know there were two spellings.

**The invariants are the ones a caller would otherwise have to re-check.** A
track with nothing on it has no first step and no next one, and an exercise
listed twice has two positions, so `position` would have to pick one and
`after` would loop. Both are refused here rather than in the loader, for the
reason every value object in this package gives: the alternative is a rule that
holds at the edge and is trusted everywhere else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from practice.domain.errors import InvalidValueError

if TYPE_CHECKING:
    from practice.domain.ids import ExerciseId

__all__ = ["Track"]

# The same shape `ids.py` uses for a slug, restated rather than imported because
# that one is private to the module that owns exercise ids. A track's name ends
# up in a URL (`/tracks/blind-75`) and in a form field, so it gets the same rule
# for the same reason.
_NAME: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class Track:
    """An ordered run of exercises with a name somebody can follow it by."""

    name: str
    title: str
    summary: str
    exercises: tuple[ExerciseId, ...]

    def __post_init__(self) -> None:
        if not _NAME.match(self.name):
            raise InvalidValueError(
                f"a track's name must be lowercase kebab-case, got {self.name!r}"
            )
        if not self.title.strip():
            raise InvalidValueError(f"track {self.name!r} needs a title")
        if not self.exercises:
            raise InvalidValueError(f"track {self.name!r} has no exercises on it")
        repeated = sorted(
            {
                exercise_id.value
                for exercise_id in self.exercises
                if self.exercises.count(exercise_id) > 1
            }
        )
        if repeated:
            raise InvalidValueError(
                f"track {self.name!r} lists twice: {', '.join(repeated)}"
            )

    def __len__(self) -> int:
        return len(self.exercises)

    def __contains__(self, exercise_id: object) -> bool:
        return exercise_id in self.exercises

    def position(self, exercise_id: ExerciseId) -> int | None:
        """Where this exercise sits, counted from zero, or `None` if it is not here.

        `None` rather than a raise: *is this exercise on that track* is a
        question a page asks about an exercise it was handed, and the answer no
        is ordinary.
        """
        try:
            return self.exercises.index(exercise_id)
        except ValueError:
            return None

    def after(self, exercise_id: ExerciseId) -> tuple[ExerciseId, ...]:
        """Every other step, starting with the one that follows this and wrapping.

        The order *what next* is searched in. It wraps because a solver who
        skipped step three and has just finished step forty should be sent back
        to three rather than told the track is over — and it starts after the
        current step rather than at the top for the opposite case: somebody who
        just failed step nine and pressed Next asked to move on, and the first
        unfinished step from the top is step nine.

        An exercise that is not on the track has nothing before it, so the
        answer is the whole track from the top.
        """
        index = self.position(exercise_id)
        if index is None:
            return self.exercises
        return self.exercises[index + 1 :] + self.exercises[:index]
