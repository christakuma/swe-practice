"""Auditing an exercise library: the half of PLAN.md §9 that lands in Phase 2."""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.adapters.content import validate_exercise, validate_library
from practice.adapters.content.validation import discover, unproven_by_design

from ..conftest import a_kata, a_scenario

if TYPE_CHECKING:
    from pathlib import Path

    from ..conftest import WriteExercise


def problems(directory: Path) -> tuple[str, ...]:
    return validate_exercise(directory).problems


# --- the happy path --------------------------------------------------------


def test_a_complete_exercise_has_no_problems(write_exercise: WriteExercise) -> None:
    assert problems(write_exercise(a_scenario())) == ()


def test_a_complete_kata_has_no_problems(write_exercise: WriteExercise) -> None:
    assert problems(write_exercise(a_kata())) == ()


def test_a_report_names_the_exercise_by_id(write_exercise: WriteExercise) -> None:
    report = validate_exercise(write_exercise(a_scenario()))

    assert report.ok
    assert report.name == "git/undo-a-commit"


# --- quality rules the domain deliberately declines to enforce -------------


def test_an_exercise_with_no_hints_is_reported(write_exercise: WriteExercise) -> None:
    """Representable, and still wrong to ship. The domain should not refuse to
    model an exercise someone is halfway through drafting (PLAN.md §4.2).
    """
    assert problems(write_exercise(a_scenario(hints=[]))) == ("has no hints",)


def test_a_missing_notes_file_is_reported(write_exercise: WriteExercise) -> None:
    """The notes are where the *why* lives, and the why is the product."""
    assert problems(write_exercise(a_scenario(), notes=None)) == (
        "notes.md: is missing or empty",
    )


def test_a_whitespace_only_notes_file_counts_as_empty(
    write_exercise: WriteExercise,
) -> None:
    assert problems(write_exercise(a_scenario(), notes="\n  \n")) == (
        "notes.md: is missing or empty",
    )


# --- files the spec names -------------------------------------------------


def test_a_missing_fixture_is_reported(write_exercise: WriteExercise) -> None:
    directory = write_exercise(a_scenario(), files={"fixture.sh": ""})

    assert problems(directory) == ("fixture.sh: named by the spec but not on disk",)


def test_a_missing_counter_example_is_reported(
    write_exercise: WriteExercise,
) -> None:
    directory = write_exercise(a_scenario(), files={"naive.cmds": ""})

    assert problems(directory) == ("naive.cmds: named by the spec but not on disk",)


def test_a_missing_kata_file_is_reported(write_exercise: WriteExercise) -> None:
    directory = write_exercise(a_kata(), files={"tests.py": ""})

    assert problems(directory) == ("tests.py: named by the spec but not on disk",)


def test_a_missing_file_is_not_also_reported_as_an_illegal_command_list(
    write_exercise: WriteExercise,
) -> None:
    """One problem, one line. A missing `solution.cmds` reported twice — once as
    absent and once as unparseable — reads as two separate things to fix.
    """
    directory = write_exercise(a_scenario(), files={"solution.cmds": ""})

    assert problems(directory) == ("solution.cmds: named by the spec but not on disk",)


# --- the PLAN.md §5.3 guarantee -------------------------------------------


def test_a_reference_command_outside_the_allowlist_is_reported(
    write_exercise: WriteExercise,
) -> None:
    """The failure §5.3 exists to prevent: a solution validated through an
    execution path the solver cannot use proves only that *a* solution exists,
    not that one exists within the rules — so a scenario could ship literally
    unsolvable with the build still green.
    """
    directory = write_exercise(
        a_scenario(), files={"solution.cmds": "git status\nsed -i s/a/b/ f.py\n"}
    )

    assert problems(directory) == (
        "solution.cmds: line 2: 'sed' is not in allowed_commands (cat, git)",
    )


def test_a_counter_example_is_held_to_the_same_policy(
    write_exercise: WriteExercise,
) -> None:
    """Counter-examples get the same guarantee, so `naive.cmds` is a fair test
    of whether the assertions discriminate rather than of what it was allowed
    to type.
    """
    directory = write_exercise(a_scenario(), files={"naive.cmds": "rm -rf .git\n"})

    assert problems(directory) == (
        "naive.cmds: line 1: 'rm' is not in allowed_commands (cat, git)",
    )


def test_a_shell_metacharacter_in_a_reference_is_reported_with_its_line(
    write_exercise: WriteExercise,
) -> None:
    """A content author has a shell and the solver does not, which is exactly
    how a redirect ends up in a solution file that cannot be replayed.
    """
    directory = write_exercise(
        a_scenario(), files={"solution.cmds": "git status\ngit log > out.txt\n"}
    )

    (problem,) = problems(directory)
    assert problem.startswith("solution.cmds: line 2:")
    assert "no shell here" in problem


def test_an_empty_reference_solution_is_reported(
    write_exercise: WriteExercise,
) -> None:
    """A scenario whose reference solution does nothing cannot be proven
    solvable by Phase 5 either, so it is worth catching now.
    """
    directory = write_exercise(a_scenario(), files={"solution.cmds": "# nothing\n"})

    assert problems(directory) == ("solution.cmds: holds no commands",)


def test_a_reference_longer_than_the_exercises_own_budget_is_reported(
    write_exercise: WriteExercise,
) -> None:
    """`max_commands` applies to the reference too. An exercise whose own
    solution cannot fit inside its budget is unsolvable, and no amount of
    replaying it in Phase 5 would say so any more clearly.
    """
    document = a_scenario()
    document["scenario"]["max_commands"] = 2
    directory = write_exercise(
        document, files={"solution.cmds": "git status\ngit log\ngit diff\n"}
    )

    assert problems(directory) == (
        "solution.cmds: 3 commands exceeds the exercise's own max_commands of 2",
    )


def test_every_illegal_line_is_reported_not_just_the_first(
    write_exercise: WriteExercise,
) -> None:
    directory = write_exercise(
        a_scenario(), files={"solution.cmds": "sed x\ngit status\nawk y\n"}
    )

    assert len(problems(directory)) == 2


# --- a file that will not load at all -------------------------------------


def test_an_unloadable_exercise_reports_the_schema_problems(
    write_exercise: WriteExercise,
) -> None:
    document = a_scenario()
    document["estimated_minutes"] = 0
    directory = write_exercise(document)

    assert problems(directory) == (
        "exercise.yaml: estimated_minutes: Input should be greater than or equal to 1",
    )


def test_an_unloadable_exercise_is_still_named_by_its_id(
    write_exercise: WriteExercise,
) -> None:
    """A report headed by an id is readable; one headed by an absolute temp path
    is not. The id is recoverable here because only the directory disagreed.
    """
    report = validate_exercise(
        write_exercise(a_scenario(), directory="git/somewhere-else")
    )

    assert not report.ok
    assert report.name == "git/undo-a-commit"


def test_an_unparseable_exercise_falls_back_to_the_directory(
    write_exercise: WriteExercise,
) -> None:
    report = validate_exercise(write_exercise(a_scenario(), raw="[not, a, mapping]\n"))

    assert report.exercise_id is None
    assert report.name.endswith("undo-a-commit")


# --- the library walk ------------------------------------------------------


def test_a_library_of_good_exercises_passes(
    library: Path, write_exercise: WriteExercise
) -> None:
    write_exercise(a_scenario())
    write_exercise(a_kata())

    report = validate_library(library)

    assert report.ok
    assert [exercise.name for exercise in report.exercises] == [
        "git/undo-a-commit",
        "katas/two-sum",
    ]


def test_an_empty_library_fails_rather_than_passing_vacuously(library: Path) -> None:
    """The same failure `test_the_walk_actually_found_the_domain` guards against
    in the architecture suite: a checker that found nothing reports success just
    as loudly as one that checked everything.
    """
    report = validate_library(library)

    assert not report.ok
    assert report.problems == ("holds no exercises",)


def test_a_content_root_that_does_not_exist_says_so(library: Path) -> None:
    report = validate_library(library / "nowhere")

    assert report.problems == ("no such directory",)


def test_an_exercise_nested_too_deep_is_reported_rather_than_skipped(
    library: Path, write_exercise: WriteExercise
) -> None:
    """The trap the two-segment `ExerciseId` rule anticipates. Globbing `*/*/`
    would make this file invisible, and "the exercise I added does not appear
    and nothing says why" is a worse half hour than a validation error.
    """
    write_exercise(a_scenario(), directory="git/advanced/undo-a-commit")
    write_exercise(a_scenario())

    report = validate_library(library)

    (problem,) = report.problems
    assert problem.startswith("git/advanced/undo-a-commit/exercise.yaml:")
    assert "<track>/<slug>" in problem
    assert not report.ok


def test_one_broken_exercise_does_not_stop_the_others_being_checked(
    library: Path, write_exercise: WriteExercise
) -> None:
    """Fixing one problem per run to discover the next is a bad afternoon, and
    with seventy exercises it stops being merely annoying.
    """
    write_exercise(a_scenario(), notes=None)
    write_exercise(a_kata(), files={"tests.py": ""})

    report = validate_library(library)

    assert len(report.failures) == 2


def test_the_walk_skips_the_shared_fixture_library(
    library: Path, write_exercise: WriteExercise
) -> None:
    """`content/_lib/` holds the shared fixture bash and is not a track."""
    underscore = library / "_lib"
    underscore.mkdir()
    (underscore / "exercise.yaml").write_text("not an exercise\n", encoding="utf-8")
    write_exercise(a_scenario())

    assert [path.name for path in discover(library)] == ["undo-a-commit"]


# --- the caveat ------------------------------------------------------------


def test_the_unproven_guarantees_are_stated_rather_than_implied() -> None:
    """A validation command that reports "3 passed" and says nothing else
    invites exactly the misreading PLAN.md §11 warns about, and the warning is
    worth more in the output than in the plan.
    """
    caveats = unproven_by_design()

    assert caveats
    assert any("nothing here is executed" in line for line in caveats)
    assert any("pytest -m content" in line for line in caveats)


def test_the_caveats_name_a_division_of_labour_and_not_a_missing_phase() -> None:
    """Every caveat this command has ever printed used to name the phase that
    would retire it. Phase 5 retired the last one, and the list that replaced it
    is permanent: `validate` runs nothing *by design*, so it will never grade a
    solution however many phases land.

    Worth a test in both directions. Dropping the caveats would imply a green
    audit covers solvability, which it does not. Leaving a phase number in them
    would promise that someday it will, which is a promise nobody intends to
    keep -- the fast offline audit has to stay usable on a machine with no git.
    """
    caveats = unproven_by_design()

    assert caveats
    assert not any("phase" in line.casefold() for line in caveats)
