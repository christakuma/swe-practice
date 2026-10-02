"""`practice validate`, driven through Typer's runner.

Integration rather than unit because the command's whole job is to read a
directory and tell you what is in it, and because the exit code is the contract
CI depends on — a test that stubbed the filesystem would verify neither.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer.testing import CliRunner

from practice.config import CONTENT_ROOT_ENV, content_root
from practice.interface.cli.main import app

from .conftest import a_kata, a_scenario

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from .conftest import WriteExercise

runner = CliRunner()


def run(*arguments: str) -> tuple[int, str]:
    result = runner.invoke(app, ["validate", *arguments])
    return result.exit_code, result.output


# --- the project's own library --------------------------------------------


def test_the_shipped_library_validates() -> None:
    """The Phase 2 exit criterion, first half: `practice validate` passes on
    the three real exercises.
    """
    code, output = run()

    assert code == 0, output
    assert "all valid" in output


def test_every_shipped_exercise_is_listed_by_id() -> None:
    """Guards the same hole as the architecture suite's "did the walk find
    anything": a run that discovered nothing exits zero just as happily.
    """
    _, output = run()

    for exercise_id in (
        "git/recover-a-lost-commit",
        "git/revert-a-pushed-commit",
        "katas/two-sum",
    ):
        assert exercise_id in output


def test_it_reports_what_a_passing_run_does_not_prove() -> None:
    """PLAN.md §11 says in as many words not to mistake green here for content
    that works, and that warning is worth more in the output than in the plan.

    The caveats used to name Phase 5 as the missing piece; they name the division
    of labour now, because `validate` runs nothing on purpose and that is the
    permanent reason rather than a temporary one.
    """
    _, output = run()

    assert "Not proven by this command:" in output
    assert "nothing here is executed" in output
    assert "pytest -m content" in output


def test_the_caveats_can_be_turned_off_for_a_terser_run() -> None:
    _, output = run("--no-caveats")

    assert "all valid" in output
    assert "Not proven" not in output


# --- a deliberately broken file -------------------------------------------


def test_a_broken_exercise_fails_the_run(write_exercise: WriteExercise) -> None:
    """The Phase 2 exit criterion, second half."""
    document = a_scenario()
    document["scenario"]["checks"][0]["assert"] = "tree_equal"
    write_exercise(document)

    code, output = run("--content-root", str(write_exercise(document).parents[1]))

    assert code == 1
    assert "1 of 1 exercise has problems" in output


def test_a_failure_is_located_down_to_the_field(
    library: Path, write_exercise: WriteExercise
) -> None:
    """ "A clear, located message" is the criterion, so the location is the
    assertion: file, then path within it, then what is wrong.
    """
    document = a_scenario()
    document["scenario"]["checks"][0]["assert"] = "tree_equal"
    write_exercise(document)

    _, output = run("--content-root", str(library))

    assert (
        "exercise.yaml: scenario.checks.0.assert: unknown assertion 'tree_equal'; "
        "did you mean tree_equals?" in output
    )


def test_a_good_exercise_is_still_reported_alongside_a_bad_one(
    library: Path, write_exercise: WriteExercise
) -> None:
    write_exercise(a_kata())
    write_exercise(a_scenario(), notes=None)

    code, output = run("--content-root", str(library))

    assert code == 1
    assert "ok   katas/two-sum" in output
    assert "FAIL git/undo-a-commit" in output
    assert "notes.md: is missing or empty" in output


def test_an_unloadable_exercise_is_headed_by_a_relative_path(
    library: Path, write_exercise: WriteExercise
) -> None:
    """The root is already the first line, and an absolute temp path in a CI
    log is worse than noise.
    """
    write_exercise(a_scenario(), raw="[not, a, mapping]\n")

    _, output = run("--content-root", str(library))

    assert "FAIL git/undo-a-commit" in output
    assert str(library) not in output.split("\n", 1)[1]


def test_an_empty_library_fails_rather_than_passing_vacuously(library: Path) -> None:
    code, output = run("--content-root", str(library))

    assert code == 1
    assert "holds no exercises" in output


def test_a_content_root_that_does_not_exist_fails_clearly(tmp_path: Path) -> None:
    code, output = run("--content-root", str(tmp_path / "nowhere"))

    assert code == 1
    assert "no such directory" in output


# --- choosing the library --------------------------------------------------


def test_the_content_root_can_come_from_the_environment(
    library: Path,
    write_exercise: WriteExercise,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CI and the content suite both point the command somewhere else, and an
    env var does that without every caller growing a flag.
    """
    write_exercise(a_kata())
    monkeypatch.setenv(CONTENT_ROOT_ENV, str(library))

    code, output = run()

    assert code == 0
    assert "katas/two-sum" in output
    assert "git/revert-a-pushed-commit" not in output


def test_the_flag_wins_over_the_environment(
    library: Path,
    write_exercise: WriteExercise,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    write_exercise(a_kata())
    monkeypatch.setenv(CONTENT_ROOT_ENV, str(tmp_path / "nowhere"))

    code, _ = run("--content-root", str(library))

    assert code == 0


def test_the_default_root_is_this_projects_content_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CONTENT_ROOT_ENV, raising=False)

    root = content_root()

    assert root.name == "content"
    assert (root / "git" / "revert-a-pushed-commit" / "exercise.yaml").is_file()


# --- the shape of the command ---------------------------------------------


def test_the_subcommand_is_required_rather_than_implied() -> None:
    """One command today, three by Phase 9. Typer collapses a single-command
    app into a bare `practice` unless there is a callback, and an invocation
    that changes shape when the second command lands is a bad invocation.
    """
    result = runner.invoke(app, [])

    assert result.exit_code != 0
    assert "validate" in result.output


def test_an_unloadable_yaml_file_does_not_produce_a_traceback(
    library: Path, write_exercise: WriteExercise
) -> None:
    """Every content problem is a report, not an exception. A traceback in the
    output means one path escaped that rule.
    """
    write_exercise(a_scenario(), raw="scenario: [1, 2\n")

    result = runner.invoke(app, ["validate", "--content-root", str(library)])

    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "Traceback" not in result.output
