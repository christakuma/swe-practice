"""Which version of an exercise to start: the standard one, a named variant, or
whichever the dice say.

**A use case of its own rather than an argument to `StartAttempt`**, and the
reason is that it answers a different question. `StartAttempt` takes an exercise
id and makes an attempt at it; it has never needed to know how the id was
arrived at, and a variant is an exercise with an id like any other (ADR 0028).
So choosing is resolved *to* an id here, and everything downstream of the id --
provisioning, policy, grading, the log -- is the path that already exists. Had
the choice been a parameter there, the one use case every surface shares would
have grown a branch that two of its three callers never take.

**The standard version is in the draw.** `RANDOM` picks among the base and its
variants alike, not among the variants only. An interviewer's twist is only a
twist if you did not know it was coming, and a draw that could never land on
the problem as written would tell a solver with one variant exactly what they
were about to get.

**Chance is a port**, for `Clock`'s reason and `IdGenerator`'s: a use case that
called `random.choice` could only be tested by patching it, and the test that
matters here is the dull one -- that every version is a candidate and nothing
else is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from practice.application.errors import ExerciseNotFoundError

if TYPE_CHECKING:
    from practice.domain.ids import ExerciseId
    from practice.domain.ports import Chooser, ContentRepository

__all__ = ["RANDOM", "ChooseVersion"]

#: The choice that is not a version's name. A word no slug can be confused with
#: only by convention, so a library that ships `variants/random` would shadow
#: it -- which `__call__` resolves in the draw's favour, by testing for it
#: first.
RANDOM: Final = "random"


@dataclass(frozen=True, slots=True)
class ChooseVersion:
    """Resolve a base exercise and a choice to the id of the version to start."""

    content: ContentRepository
    chooser: Chooser

    def __call__(
        self, exercise_id: ExerciseId, choice: str | None = None
    ) -> ExerciseId:
        """The id to hand `StartAttempt`.

        No choice -- `None`, or the empty string an unselected form field sends
        -- is the standard version, which is what keeps every caller written
        before variants existed meaning what it meant.

        A variant is named by its slug or by its whole id, because the terminal
        wants the short one and a form's `<option>` holds the long one. Naming
        one that is not a variant *of this exercise* is refused with the names
        that would have worked: a variant of something else is a real exercise,
        and starting it from here would be a typo landing on the wrong problem.
        """
        if self.content.get(exercise_id) is None:
            raise ExerciseNotFoundError(f"no exercise with id {exercise_id}")
        if not choice:
            return exercise_id

        variants = self.content.variants_of(exercise_id)
        if choice == RANDOM:
            return self.chooser.choose(
                (exercise_id, *(variant.id for variant in variants))
            )

        for variant in variants:
            if choice in {variant.id.value, variant.id.slug}:
                return variant.id

        offered = ", ".join(variant.id.slug for variant in variants) or "none"
        raise ExerciseNotFoundError(
            f"{exercise_id} has no variant called {choice!r}; its variants are: "
            f"{offered}"
        )
