"""Which grader runs which kind, and what happens when none does.

The interesting case is still the missing one, even though both shipped kinds now
have a grader. A registry with an entry for everything is a dict with a lookup;
what makes this worth testing is the day a third kind is added -- SQL exercises are
parked in Phase 13 -- and the refusal has to name the gap rather than fail with an
`AttributeError` somewhere downstream, or worse, provision a workspace and run a
fixture before discovering it.

So these cases deliberately build registries that are *missing* something, rather
than asserting against whatever `build_graders` currently returns. That is also why
they kept working across Phase 5, which registered the half they used to be about.
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


def test_it_refuses_a_kind_nothing_can_grade_and_says_what_it_does_have() -> None:
    """The refusal is the feature. A kind with no grader has to produce a readable
    message naming what *is* registered, so whoever reads it can tell "not built
    yet" from "wired up wrong".
    """
    registry = a_registry()

    assert not registry.supports(a_scenario())
    with pytest.raises(UnsupportedExerciseKindError, match="registered for kata"):
        registry.for_exercise(a_scenario())


def test_an_empty_registry_says_so_rather_than_naming_nothing() -> None:
    """The degenerate case, which is what a misconfigured composition root looks
    like from here.
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
