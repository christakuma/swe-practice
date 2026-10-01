"""Which grader runs which kind, and what happens when none does.

The interesting case is the missing one. A registry with an entry for every kind
would be a dict with a lookup; what makes this worth testing is that
`git_scenario` has no grader until Phase 5, and the refusal has to name the gap
rather than fail with an `AttributeError` somewhere downstream.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.application.errors import UnsupportedExerciseKindError
from practice.application.registry import GraderRegistry
from practice.domain.exercise import ExerciseKind
from tests.fakes import a_kata, a_scenario

if TYPE_CHECKING:
    from practice.domain.verdict import Verdict


class NullGrader:
    """Satisfies `Grader` and is never asked to do anything interesting."""

    def grade(self, exercise: object, workspace: object, attempt: object) -> Verdict:
        del exercise, workspace, attempt
        raise NotImplementedError


def a_registry() -> GraderRegistry:
    return GraderRegistry(graders={ExerciseKind.KATA: NullGrader()})


def test_it_returns_the_grader_for_a_registered_kind() -> None:
    registry = a_registry()

    assert isinstance(registry.for_exercise(a_kata()), NullGrader)
    assert registry.supports(a_kata())


def test_it_refuses_a_kind_nothing_can_grade_and_names_the_phase() -> None:
    """The refusal is the feature: a solver asking for a git scenario today
    should be told that the engine lands in Phase 5, not handed a traceback or,
    worse, a kata-shaped verdict.
    """
    registry = a_registry()

    assert not registry.supports(a_scenario())
    with pytest.raises(UnsupportedExerciseKindError, match="phase 5"):
        registry.for_exercise(a_scenario())


def test_an_empty_registry_says_what_it_does_have() -> None:
    """The fallback message, for a kind with no phase note — which is what a
    third exercise kind would be on the day it is added.
    """
    registry = GraderRegistry(graders={})

    with pytest.raises(UnsupportedExerciseKindError, match="registered for none"):
        registry.for_exercise(a_kata())


def test_the_registry_cannot_be_extended_after_it_is_built() -> None:
    """A caller that kept the dict it passed in must not be able to register a
    grader behind the composition root's back — the whole value of one wiring
    point is that the graph it built is the graph that runs.
    """
    graders: dict[ExerciseKind, NullGrader] = {ExerciseKind.KATA: NullGrader()}
    registry = GraderRegistry(graders=graders)

    graders[ExerciseKind.GIT_SCENARIO] = NullGrader()

    assert not registry.supports(a_scenario())
