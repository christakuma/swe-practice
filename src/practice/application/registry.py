"""The exercise-kind registry: which grader runs which kind.

The dispatch PLAN.md §3 puts in the application layer and the reason `Grader` is
a port rather than a method on `Exercise` — the domain must not know that a kata
is graded by running pytest.

**One entry today, and it still earns its place.** §13's rule is that an
abstraction with one implementation gets deleted, and this is not that: it is
one implementation of a *two*-kind enum, so the interesting case is the missing
one. Without the registry, asking for a git scenario would reach a grader that
is not there and fail with an `AttributeError` or, worse, provision a workspace
and run a fixture before discovering it. With it, the refusal happens before
anything is built and says which phase lands the missing half.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from practice.application.errors import UnsupportedExerciseKindError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.domain.exercise import Exercise, ExerciseKind
    from practice.domain.ports import Grader

__all__ = ["GraderRegistry"]

#: What to say about a kind nothing can grade yet. Keyed by the enum *value* so
#: this module does not have to import the enum at runtime.
_PENDING: Mapping[str, str] = MappingProxyType(
    {"git_scenario": "the git scenario engine lands in phase 5"}
)


@dataclass(frozen=True, slots=True)
class GraderRegistry:
    """Graders by exercise kind."""

    graders: Mapping[ExerciseKind, Grader]

    def __post_init__(self) -> None:
        # A read-only view, so a caller that kept its dict cannot register a
        # grader after the composition root has handed the registry out.
        object.__setattr__(self, "graders", MappingProxyType(dict(self.graders)))

    def supports(self, exercise: Exercise) -> bool:
        return exercise.kind in self.graders

    def for_exercise(self, exercise: Exercise) -> Grader:
        """The grader for this exercise, or a refusal that names the gap."""
        grader = self.graders.get(exercise.kind)
        if grader is None:
            raise UnsupportedExerciseKindError(
                f"{exercise.id} is a {exercise.kind.value} and nothing registered "
                f"can grade one: {self._reason(exercise.kind)}"
            )
        return grader

    def _reason(self, kind: ExerciseKind) -> str:
        known = ", ".join(sorted(registered.value for registered in self.graders))
        return _PENDING.get(kind.value, f"graders are registered for {known or 'none'}")
