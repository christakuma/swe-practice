"""A content library in a dict, and the two exercises most tests want.

`FakeContentRepository` is the second implementation of `ContentRepository`, and
the filter matching is the part worth being careful about: it delegates to
`ExerciseFilter.matches` rather than reimplementing the comparison, which is the
same reason the domain owns that method at all — a fake that decided for itself
what a filter means would stop being evidence about the real repository
(PLAN.md §4.2).

The builders exist because an `Exercise` has ten required fields and nine of
them are noise in any given test. They take overrides for the fields a test is
actually about.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.exercise import (
    CheckSpec,
    ComplexityExpectation,
    Difficulty,
    Exercise,
    ExerciseKind,
    GitScenarioSpec,
    Hint,
    KataSpec,
)
from practice.domain.ids import ExerciseId, tag
from practice.domain.verdict import Severity

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from practice.domain.exercise import ExerciseFilter

__all__ = ["FakeContentRepository", "a_kata", "a_scenario"]


def a_kata(
    *,
    exercise_id: str = "katas/two-sum",
    complexity: ComplexityExpectation | None = None,
    time_limit_seconds: int = 10,
    estimated_minutes: int = 15,
    hints: tuple[str, ...] = ("Trade space for time.",),
    tags: tuple[str, ...] = ("arrays", "hash-map"),
) -> Exercise:
    """A kata whose files are named the way the real ones are.

    The three Phase 9 overrides -- the estimate, the hint list and the tags --
    exist because the grade suggestion reads the first two and tag mastery reads
    the third, and a fake with one hint and a fixed estimate can only express one
    of the cases those rules distinguish.
    """
    return Exercise(
        id=ExerciseId(exercise_id),
        kind=ExerciseKind.KATA,
        title="Two Sum",
        prompt="Return the two positions whose values add up to the target.",
        difficulty=Difficulty.EASY,
        tags=tuple(tag(name) for name in tags),
        estimated_minutes=estimated_minutes,
        hints=tuple(Hint(text) for text in hints),
        notes="Why a dict beats two loops.",
        spec=KataSpec(
            language="python",
            stub="stub.py",
            tests="tests.py",
            reference="solution.py",
            time_limit_seconds=time_limit_seconds,
            complexity=complexity,
        ),
    )


def a_scenario(*, exercise_id: str = "git/revert-a-pushed-commit") -> Exercise:
    """A git scenario: the kind nothing can grade until Phase 5."""
    return Exercise(
        id=ExerciseId(exercise_id),
        kind=ExerciseKind.GIT_SCENARIO,
        title="Revert a pushed commit",
        prompt="Undo it without rewriting published history.",
        difficulty=Difficulty.MEDIUM,
        tags=(tag("history"),),
        estimated_minutes=20,
        hints=(Hint("What does your teammate already have?"),),
        notes="Why revert and not reset.",
        spec=GitScenarioSpec(
            fixture="fixture.sh",
            reference="solution.cmds",
            checks=(
                CheckSpec(
                    id="history-preserved",
                    label="The bad commit is still reachable.",
                    severity=Severity.REQUIRED,
                    assertion="is_ancestor",
                    explanation="Published history is not yours to rewrite.",
                ),
            ),
            allowed_commands=frozenset({"git", "cat"}),
        ),
    )


class FakeContentRepository:
    """Satisfies `practice.domain.ports.ContentRepository` from a dict."""

    def __init__(self, exercises: Iterable[Exercise] = ()) -> None:
        self._exercises = {exercise.id: exercise for exercise in exercises}

    def list_exercises(
        self, criteria: ExerciseFilter | None = None
    ) -> Sequence[Exercise]:
        """Sorted by id, like the filesystem repository, so output is stable."""
        found = [
            exercise
            for exercise in self._exercises.values()
            if criteria is None or criteria.matches(exercise)
        ]
        return sorted(found, key=lambda exercise: exercise.id)

    def get(self, exercise_id: ExerciseId) -> Exercise | None:
        return self._exercises.get(exercise_id)

    def add(self, *exercises: Exercise) -> None:
        """Put more exercises in the library.

        For the tests that need a library bigger than the two shipped fakes --
        a dashboard that cuts its queue cannot be tested against a queue that is
        shorter than the cut.
        """
        for exercise in exercises:
            self._exercises[exercise.id] = exercise

    def forget(self, exercise_id: ExerciseId) -> None:
        """Remove an exercise, for the test about a library that changed under a
        live attempt — the one case `SubmitSolution` cannot recover from.
        """
        self._exercises.pop(exercise_id, None)

    def replace_with(self, exercise: Exercise) -> None:
        """Edit an exercise under a live attempt, keeping its id.

        The other half of `forget`, and the half that tests the subtler claim: an
        `Attempt` copies the limits and the hint list in at construction (§4.3), so
        a library edited mid-attempt must not change what that attempt is held to
        -- or what its own log is an index into.
        """
        self._exercises[exercise.id] = exercise
