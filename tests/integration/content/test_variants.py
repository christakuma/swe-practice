"""Variants on disk: what the repository lists, and what `validate` refuses.

A variant is an exercise with a `variant:` block (ADR 0028), and the two things
that makes true about a library are both here. The repository must *load* one
and never *list* it -- reachable by id and under its base, absent from the
listing the curriculum orders. And three library-level rules stop one being
unreachable or absurd: its base must exist, must be a standard exercise, and
must be the same kind.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from practice.adapters.content import FilesystemContentRepository
from practice.adapters.content.validation import validate_library
from practice.domain.ids import ExerciseId

from ..conftest import a_kata, a_scenario

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.ports import ContentRepository

    from ..conftest import WriteExercise

BASE = ExerciseId("katas/two-sum")


def a_variant(
    slug: str, *, of: str = "katas/two-sum", **overrides: Any
) -> dict[str, Any]:
    """A kata that says whose twist it is. Never placed in the curriculum."""
    return a_kata(
        id=f"variants/{slug}",
        title=f"Two Sum, {slug}",
        variant={"of": of, "twist": "The list is sorted."},
        **overrides,
    )


@pytest.fixture
def stocked(library: Path, write_exercise: WriteExercise) -> Path:
    """A kata, a scenario, and two variants of the kata written out of id order."""
    write_exercise(a_kata())
    write_exercise(a_scenario())
    write_exercise(a_variant("sorted"), curriculum=False)
    write_exercise(a_variant("backwards"), curriculum=False)
    return library


# --- the repository -----------------------------------------------------------


def test_a_variant_is_not_listed(stocked: Path) -> None:
    """Four exercises on disk and two in the listing, which is what every
    count of the library, every track and the unseen half of the review queue
    inherit without knowing variants exist.
    """
    repository: ContentRepository = FilesystemContentRepository(stocked)

    assert [str(exercise.id) for exercise in repository.list_exercises()] == [
        "katas/two-sum",
        "git/undo-a-commit",
    ]


def test_a_variant_is_found_by_its_id(stocked: Path) -> None:
    """All an attempt, a resumed workbench or a tutor has ever asked for."""
    found = FilesystemContentRepository(stocked).get(ExerciseId("variants/sorted"))

    assert found is not None
    assert found.variant is not None
    assert found.variant.of == BASE
    assert found.variant.twist == "The list is sorted."


def test_the_variants_of_an_exercise_come_back_in_id_order(stocked: Path) -> None:
    """Written `sorted` then `backwards`; returned by id, so a form's options
    do not reshuffle with the filesystem's mood.
    """
    variants = FilesystemContentRepository(stocked).variants_of(BASE)

    assert [str(variant.id) for variant in variants] == [
        "variants/backwards",
        "variants/sorted",
    ]


def test_an_exercise_without_variants_has_none(stocked: Path) -> None:
    repository = FilesystemContentRepository(stocked)

    assert repository.variants_of(ExerciseId("git/undo-a-commit")) == []
    assert repository.variants_of(ExerciseId("katas/not-there")) == []


def test_a_variant_has_no_variants_of_its_own(stocked: Path) -> None:
    repository = FilesystemContentRepository(stocked)

    assert repository.variants_of(ExerciseId("variants/sorted")) == []


def test_a_library_of_only_variants_lists_nothing(
    library: Path, write_exercise: WriteExercise
) -> None:
    """And does not go looking for a curriculum to order nothing with."""
    write_exercise(a_variant("sorted"), curriculum=False)

    assert FilesystemContentRepository(library).list_exercises() == []


# --- validation -----------------------------------------------------------------


def test_a_library_with_variants_is_valid_without_placing_them(stocked: Path) -> None:
    """The curriculum names the two standard exercises and neither variant,
    and that is the whole of what it has to name.
    """
    report = validate_library(stocked)

    assert report.ok, report.problems
    assert len(report.exercises) == 4


def test_a_variant_named_in_the_curriculum_is_refused(
    stocked: Path, write_exercise: WriteExercise
) -> None:
    """By subtraction: a variant is not among the exercises the manifest may
    place, so naming one is naming something that is not there.
    """
    write_exercise(a_variant("placed"))

    report = validate_library(stocked)

    assert report.problems == (
        "curriculum.yaml: lists exercise(s) that are not on disk: variants/placed",
    )


def test_a_variant_of_nothing_is_refused(
    stocked: Path, write_exercise: WriteExercise
) -> None:
    """On disk, graded by the suite, and offered under no exercise at all."""
    write_exercise(a_variant("orphan", of="katas/three-sum"), curriculum=False)

    report = validate_library(stocked)

    assert report.problems == (
        (
            "variants/orphan/exercise.yaml: is a variant of katas/three-sum, which "
            "is not in the library"
        ),
    )


def test_a_variant_of_a_variant_is_refused(
    stocked: Path, write_exercise: WriteExercise
) -> None:
    """`variants_of` goes one level deep, so this would be as unreachable as
    an orphan -- and the message says why rather than leaving it to be found.
    """
    write_exercise(a_variant("twice", of="variants/sorted"), curriculum=False)

    report = validate_library(stocked)

    assert report.problems == (
        (
            "variants/twice/exercise.yaml: is a variant of variants/sorted, which is "
            "itself a variant; a twist is on a standard exercise"
        ),
    )


def test_a_variant_of_another_kind_is_refused(
    stocked: Path, write_exercise: WriteExercise
) -> None:
    write_exercise(a_variant("console", of="git/undo-a-commit"), curriculum=False)

    report = validate_library(stocked)

    assert report.problems == (
        (
            "variants/console/exercise.yaml: is a kata and a variant of "
            "git/undo-a-commit, which is a git_scenario"
        ),
    )


def test_a_variant_is_audited_like_any_other_exercise(
    stocked: Path, write_exercise: WriteExercise
) -> None:
    """Being unlisted is not being unchecked: its files and its notes are held
    to what a standard kata's are.
    """
    write_exercise(a_variant("bare"), curriculum=False, notes=None)

    report = validate_library(stocked)

    assert [failure.name for failure in report.failures] == ["variants/bare"]
