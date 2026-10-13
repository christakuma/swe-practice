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
    Example,
    Exercise,
    ExerciseKind,
    GitScenarioSpec,
    Hint,
    KataSpec,
    SqlDrillSpec,
    Variant,
)
from practice.domain.ids import ExerciseId, tag
from practice.domain.verdict import Severity

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from practice.domain.exercise import ExerciseFilter
    from practice.domain.track import Track

__all__ = ["FakeContentRepository", "a_drill", "a_kata", "a_scenario"]


def a_kata(
    *,
    exercise_id: str = "katas/two-sum",
    complexity: ComplexityExpectation | None = None,
    time_limit_seconds: int = 10,
    estimated_minutes: int = 15,
    hints: tuple[str, ...] = ("Trade space for time.",),
    tags: tuple[str, ...] = ("arrays", "hash-map"),
    constraints: tuple[str, ...] = (),
    examples: tuple[Example, ...] = (),
    title: str = "Two Sum",
    variant: Variant | None = None,
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
        title=title,
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
            constraints=constraints,
            examples=examples,
        ),
        variant=variant,
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


def a_drill(
    *,
    exercise_id: str = "sql/one-row-per-customer",
    checks: tuple[CheckSpec, ...] = (),
    estimated_minutes: int = 12,
    hints: tuple[str, ...] = ("Which side of the join keeps its rows?",),
    tags: tuple[str, ...] = ("joins", "aggregation"),
) -> Exercise:
    """A SQL drill, named and shaped like the real ones.

    `checks` is overridable and defaults to one required `result_matches`,
    because the drill grader's interesting cases are all about *which* checks
    ran -- which is the opposite of `a_kata`, whose checks come out of a test
    suite and cannot be stated here at all.
    """
    return Exercise(
        id=ExerciseId(exercise_id),
        kind=ExerciseKind.SQL_DRILL,
        title="One row per customer",
        prompt="Return every customer with how many orders they have placed.",
        difficulty=Difficulty.EASY,
        tags=tuple(tag(name) for name in tags),
        estimated_minutes=estimated_minutes,
        hints=tuple(Hint(text) for text in hints),
        notes="Why a LEFT JOIN and not an INNER one.",
        spec=SqlDrillSpec(
            seed="seed.sql",
            stub="stub.sql",
            reference="solution.sql",
            checks=checks
            or (
                CheckSpec(
                    id="rows-match",
                    label="Every customer appears exactly once, with their count.",
                    severity=Severity.REQUIRED,
                    assertion="result_matches",
                    # Params, not just an assertion name. A default check with
                    # no `with:` mapping evaluates to "this exercise is
                    # misconfigured", so a test using the builder's default
                    # would get an authoring error where it expected a grade.
                    params={"rows": (("alice", 2), ("bob", 0), ("carol", 1))},
                    explanation="A customer with no orders still has a row.",
                ),
            ),
        ),
    )


class FakeContentRepository:
    """Satisfies `practice.domain.ports.ContentRepository` from a dict."""

    def __init__(
        self, exercises: Iterable[Exercise] = (), tracks: Iterable[Track] = ()
    ) -> None:
        self._exercises = {exercise.id: exercise for exercise in exercises}
        self._tracks = tuple(tracks)

    def list_exercises(
        self, criteria: ExerciseFilter | None = None
    ) -> Sequence[Exercise]:
        """Sorted by id, like the filesystem repository, so output is stable."""
        found = [
            exercise
            for exercise in self._exercises.values()
            if not exercise.is_variant
            and (criteria is None or criteria.matches(exercise))
        ]
        return sorted(found, key=lambda exercise: exercise.id)

    def get(self, exercise_id: ExerciseId) -> Exercise | None:
        return self._exercises.get(exercise_id)

    def variants_of(self, exercise_id: ExerciseId) -> Sequence[Exercise]:
        """Held to the real repository's two rules: unlisted, and sorted by id."""
        return sorted(
            (
                exercise
                for exercise in self._exercises.values()
                if exercise.variant is not None and exercise.variant.of == exercise_id
            ),
            key=lambda exercise: exercise.id,
        )

    def list_tracks(self) -> Sequence[Track]:
        """The tracks this fake was given, in the order it was given them.

        Handed over already built rather than resolved from a declaration,
        which is the one place this differs from the real repositories on
        purpose: resolution is `adapters/content/tracks.py`'s job and has its
        own tests, and a fake that re-did it would be a second implementation
        of the thing under test. What is held to the real behaviour is the part
        a use case can observe -- declaration order, and empty by default.
        """
        return self._tracks

    def offer(self, *tracks: Track) -> None:
        """Declare more tracks, after the ones already here."""
        self._tracks = (*self._tracks, *tracks)

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
