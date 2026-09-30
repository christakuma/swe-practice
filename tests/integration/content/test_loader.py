"""Reading one exercise directory off disk."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import ContentError, load_exercise
from practice.domain.exercise import ExerciseKind, GitScenarioSpec

from ..conftest import a_kata, a_scenario

if TYPE_CHECKING:
    from pathlib import Path

    from ..conftest import WriteExercise


def test_a_scenario_directory_becomes_an_exercise(
    write_exercise: WriteExercise,
) -> None:
    directory = write_exercise(a_scenario(), notes="# Why revert\n")

    exercise = load_exercise(directory)

    assert str(exercise.id) == "git/undo-a-commit"
    assert exercise.kind is ExerciseKind.GIT_SCENARIO
    assert exercise.notes == "# Why revert\n"
    assert isinstance(exercise.spec, GitScenarioSpec)


def test_a_kata_directory_becomes_an_exercise(write_exercise: WriteExercise) -> None:
    directory = write_exercise(a_kata())

    assert load_exercise(directory).kind is ExerciseKind.KATA


def test_notes_come_from_the_file_beside_the_yaml_not_from_it(
    write_exercise: WriteExercise,
) -> None:
    """`notes.md` is prose with headings and code fences in it. Keeping it out of
    the YAML means an author edits Markdown in a Markdown file.
    """
    directory = write_exercise(a_scenario(), notes="## The two routes\n\n```\ngit\n```")

    assert load_exercise(directory).notes.startswith("## The two routes")


def test_a_missing_notes_file_loads_as_empty_notes(
    write_exercise: WriteExercise,
) -> None:
    """Not a load failure. "Notes are non-empty" is a rule about a *good*
    exercise, not a representable one, so it belongs to validation — the same
    line PLAN.md §4.2 draws inside the domain.
    """
    directory = write_exercise(a_scenario(), notes=None)

    assert load_exercise(directory).notes == ""


def test_the_id_must_match_the_directory_it_is_in(
    write_exercise: WriteExercise,
) -> None:
    """The id *is* the content path (PLAN.md §4.1). A file that disagrees with
    its own directory is exactly the drift that rule exists to stop, so it is
    refused rather than resolved in favour of one of them.
    """
    directory = write_exercise(a_scenario(), directory="git/something-else")

    with pytest.raises(ContentError) as caught:
        load_exercise(directory)

    assert caught.value.problems == (
        (
            "id: 'git/undo-a-commit' does not match the directory it is in; "
            "expected 'git/something-else'"
        ),
    )


def test_a_missing_exercise_file_names_the_file(library: Path) -> None:
    directory = library / "git" / "empty"
    directory.mkdir(parents=True)

    with pytest.raises(ContentError) as caught:
        load_exercise(directory)

    assert caught.value.path.name == "exercise.yaml"
    assert caught.value.problems == ("no such file",)


def test_malformed_yaml_is_reported_with_its_line_and_column(
    write_exercise: WriteExercise,
) -> None:
    """A syntax error without a position is the one case where the reader has
    to go hunting, so the mark PyYAML found is worth unpacking.
    """
    directory = write_exercise(a_scenario(), raw="id: git/x\n  bad: [1, 2\n")

    with pytest.raises(ContentError) as caught:
        load_exercise(directory)

    (problem,) = caught.value.problems
    assert problem.startswith("line 2, column ")


def test_an_empty_file_says_so(write_exercise: WriteExercise) -> None:
    directory = write_exercise(a_scenario(), raw="# just a comment\n")

    with pytest.raises(ContentError) as caught:
        load_exercise(directory)

    assert caught.value.problems == ("is empty",)


def test_a_yaml_file_that_is_not_a_mapping_says_so(
    write_exercise: WriteExercise,
) -> None:
    """A list of exercises in one file is a plausible mistake, and `validate_python`
    on a list reports something about union tags rather than about the shape.
    """
    directory = write_exercise(a_scenario(), raw="- id: git/undo-a-commit\n")

    with pytest.raises(ContentError) as caught:
        load_exercise(directory)

    assert caught.value.problems == ("must be a mapping of keys, not a list",)


def test_schema_problems_are_reported_with_their_location(
    write_exercise: WriteExercise,
) -> None:
    document = a_scenario()
    document["scenario"]["checks"][0]["assert"] = "tree_equal"
    directory = write_exercise(document)

    with pytest.raises(ContentError) as caught:
        load_exercise(directory)

    assert caught.value.problems == (
        (
            "scenario.checks.0.assert: unknown assertion 'tree_equal'; "
            "did you mean tree_equals?"
        ),
    )


def test_every_schema_problem_is_reported_at_once(
    write_exercise: WriteExercise,
) -> None:
    document = a_scenario()
    document["estimated_minutes"] = 0
    document["scenario"]["checks"][0]["severity"] = "advisory"
    directory = write_exercise(document)

    with pytest.raises(ContentError) as caught:
        load_exercise(directory)

    assert len(caught.value.problems) == 2


def test_the_error_renders_as_the_path_then_the_problems(
    write_exercise: WriteExercise,
) -> None:
    """This string is what `practice validate` prints and what an author reads,
    so its shape is part of the contract rather than an implementation detail.
    """
    directory = write_exercise(a_scenario(), raw="- nope\n")

    with pytest.raises(ContentError) as caught:
        load_exercise(directory)

    rendered = str(caught.value)
    assert rendered.splitlines()[0].endswith("exercise.yaml")
    assert rendered.splitlines()[1] == "  must be a mapping of keys, not a list"
