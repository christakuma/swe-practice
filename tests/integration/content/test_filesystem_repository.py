"""`FilesystemContentRepository` — the `ContentRepository` port over a directory."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import ContentError, FilesystemContentRepository
from practice.domain.exercise import Difficulty, ExerciseFilter, ExerciseKind
from practice.domain.ids import ExerciseId, tag

from .conftest import a_kata, a_scenario

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.ports import ContentRepository

    from .conftest import WriteExercise


@pytest.fixture
def stocked(library: Path, write_exercise: WriteExercise) -> Path:
    """Two exercises, one of each kind, written in reverse id order.

    Reverse on purpose: a repository that happens to return them in filesystem
    order would pass an ordering assertion written against insertion order.
    """
    write_exercise(a_kata())
    write_exercise(a_scenario())
    return library


def test_it_satisfies_the_content_repository_port(stocked: Path) -> None:
    """Structural, not nominal — the port is a `Protocol`, so this class never
    imports it and the dependency arrow keeps pointing inward (ADR 0002).
    """
    repository: ContentRepository = FilesystemContentRepository(stocked)

    assert len(repository.list_exercises()) == 2


def test_listing_is_ordered_by_id(stocked: Path) -> None:
    """Deterministic without the caller inventing a sort key, which is why
    `ExerciseId` is `order=True`.
    """
    repository = FilesystemContentRepository(stocked)

    assert [str(exercise.id) for exercise in repository.list_exercises()] == [
        "git/undo-a-commit",
        "katas/two-sum",
    ]


def test_get_returns_the_exercise(stocked: Path) -> None:
    repository = FilesystemContentRepository(stocked)

    exercise = repository.get(ExerciseId("katas/two-sum"))

    assert exercise is not None
    assert exercise.title == "Two Sum"


def test_get_returns_none_for_an_exercise_that_is_not_there(stocked: Path) -> None:
    """`None` rather than an exception: "no such exercise" is a 404 on a URL
    someone bookmarked, not a fault.
    """
    repository = FilesystemContentRepository(stocked)

    assert repository.get(ExerciseId("git/nonexistent")) is None


def test_an_empty_library_lists_nothing_without_complaining(library: Path) -> None:
    """Whether an empty library is a problem is `practice validate`'s call. A
    repository asked to list an empty directory has listed it correctly.
    """
    assert FilesystemContentRepository(library).list_exercises() == []


# --- filtering -------------------------------------------------------------


def test_filtering_by_kind(stocked: Path) -> None:
    repository = FilesystemContentRepository(stocked)

    found = repository.list_exercises(
        ExerciseFilter(kinds=frozenset({ExerciseKind.KATA}))
    )

    assert [str(exercise.id) for exercise in found] == ["katas/two-sum"]


def test_filtering_by_difficulty(stocked: Path) -> None:
    repository = FilesystemContentRepository(stocked)

    found = repository.list_exercises(
        ExerciseFilter(difficulties=frozenset({Difficulty.MEDIUM}))
    )

    assert [str(exercise.id) for exercise in found] == ["git/undo-a-commit"]


def test_filtering_by_tag_matches_on_intersection(stocked: Path) -> None:
    """Any one of the tags, not all of them — the rule lives in
    `ExerciseFilter.matches` so this repository and any in-memory fake cannot
    disagree about what a filter means.
    """
    repository = FilesystemContentRepository(stocked)

    found = repository.list_exercises(
        ExerciseFilter(tags=frozenset({tag("history"), tag("nothing-has-this")}))
    )

    assert [str(exercise.id) for exercise in found] == ["git/undo-a-commit"]


def test_an_empty_filter_constrains_nothing(stocked: Path) -> None:
    repository = FilesystemContentRepository(stocked)

    assert len(repository.list_exercises(ExerciseFilter())) == 2


def test_dimensions_combine_as_and(stocked: Path) -> None:
    repository = FilesystemContentRepository(stocked)

    found = repository.list_exercises(
        ExerciseFilter(
            kinds=frozenset({ExerciseKind.KATA}),
            difficulties=frozenset({Difficulty.MEDIUM}),
        )
    )

    assert found == []


# --- failure and caching ---------------------------------------------------


def test_a_broken_exercise_fails_the_listing_rather_than_vanishing(
    library: Path, write_exercise: WriteExercise
) -> None:
    """Skipping what will not load is how an exercise disappears without anyone
    noticing: the tool looks healthy and is quietly one exercise smaller.
    `practice validate` exists so this is caught in CI, not at runtime.
    """
    write_exercise(a_scenario())
    write_exercise(a_kata(estimated_minutes=0))

    with pytest.raises(ContentError) as caught:
        FilesystemContentRepository(library).list_exercises()

    assert "estimated_minutes" in str(caught.value)


def test_the_library_is_read_once_and_cached(
    stocked: Path, write_exercise: WriteExercise
) -> None:
    """Content is read-only at runtime, so a stat on every call would buy
    nothing. If reload ever becomes a feature it gets an explicit method.
    """
    repository = FilesystemContentRepository(stocked)
    before = repository.list_exercises()

    write_exercise(a_scenario(id="git/added-later"), directory="git/added-later")

    assert repository.list_exercises() == before
    assert FilesystemContentRepository(stocked).list_exercises() != before
