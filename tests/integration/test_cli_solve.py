"""`practice solve`, driven through Typer's runner against the real library.

Integration rather than unit, for the reason the other CLI suites give: the job
of the command is to assemble the real graph and run a real subprocess, and a
test that stubbed either would verify neither. The exit code is the contract —
0 passes, 1 fails, 2 could not be run — and it is what a human in a terminal and
a future CI step both read.

Every invocation points `--workspace-root` at a temp directory. A suite that
provisioned into the user cache would collide with a session the developer has
open, and `practice gc` would report test leftovers as real attempts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from practice.config import content_root
from practice.interface.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

TWO_SUM = "katas/two-sum"
SCENARIO = "git/revert-a-pushed-commit"

runner = CliRunner()


@pytest.fixture
def workspaces(tmp_path: Path) -> Path:
    return tmp_path / "ws"


def solve(workspaces: Path, *arguments: str) -> tuple[int, str]:
    result = runner.invoke(
        app,
        ["solve", *arguments, "--workspace-root", str(workspaces), "--no-prompt"],
    )
    return result.exit_code, result.output


# --- the happy path --------------------------------------------------------


def test_the_reference_solution_passes_and_exits_zero(workspaces: Path) -> None:
    code, output = solve(
        workspaces, TWO_SUM, "--reference", "--time", "O(n)", "--space", "O(n)"
    )

    assert code == 0, output
    assert "PASS" in output
    assert "FAIL" not in output


def test_a_pass_with_no_complexity_claim_still_exits_zero(
    workspaces: Path,
) -> None:
    """`PASS_WITH_ADVISORIES` means the goal was met, so the exit code says so.
    An advisory that failed the command would make the §4.4 severity split
    pointless — it would just be a second kind of required check.
    """
    code, output = solve(workspaces, TWO_SUM, "--reference")

    assert code == 0, output
    assert "PASS, with advisories" in output
    assert "You declared the cost of your solution." in output


def test_a_solution_from_a_file_is_what_gets_graded(
    workspaces: Path, tmp_path: Path
) -> None:
    mine = tmp_path / "mine.py"
    mine.write_text(
        "def two_sum(numbers, target):\n"
        "    seen = {}\n"
        "    for index, value in enumerate(numbers):\n"
        "        if target - value in seen:\n"
        "            return (seen[target - value], index)\n"
        "        seen[value] = index\n"
        "    raise ValueError('no pair')\n",
        encoding="utf-8",
    )

    code, output = solve(workspaces, TWO_SUM, "--source", str(mine))

    assert code == 0, output
    assert str(mine) in output


def test_the_prompt_is_printed_when_it_is_asked_for(workspaces: Path) -> None:
    result = runner.invoke(
        app,
        [
            "solve",
            TWO_SUM,
            "--reference",
            "--workspace-root",
            str(workspaces),
            "--prompt",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "two_sum([2, 7, 11, 15], 9)" in result.output


# --- the failing path ------------------------------------------------------


def test_the_stub_fails_and_exits_one(workspaces: Path) -> None:
    """The default with no solution given, so the first run of the command shows
    the suite working rather than an error about missing arguments.
    """
    code, output = solve(workspaces, TWO_SUM)

    assert code == 1
    assert "FAIL" in output
    assert "stub.py (the exercise's own)" in output
    assert "NotImplementedError" in output


def test_a_failure_repeats_what_has_to_change_under_the_outcome(
    workspaces: Path,
) -> None:
    """A nine-test kata pushes the first failure off the top of a short
    terminal, so the outcome line carries the failures with it.
    """
    _, output = solve(workspaces, TWO_SUM)

    summary = output.rpartition("FAIL\n")[2]
    assert "  - Finds the two positions that add up to the target." in summary


# --- what it refuses -------------------------------------------------------


def test_a_git_scenario_is_refused_with_the_phase_that_lands_it(
    workspaces: Path,
) -> None:
    code, output = solve(workspaces, SCENARIO)

    assert code == 2
    assert "phase 5" in output


def test_an_unknown_exercise_is_refused(workspaces: Path) -> None:
    code, output = solve(workspaces, "katas/does-not-exist")

    assert code == 2
    assert "no exercise with id katas/does-not-exist" in output


def test_an_id_that_is_not_an_id_is_refused(workspaces: Path) -> None:
    """Rejected by the value object before any adapter is asked, which is the
    point of validating on construction (PLAN.md §4.1).
    """
    code, output = solve(workspaces, "two-sum")

    assert code == 2
    assert "<track>/<slug>" in output


def test_source_and_reference_together_are_refused(
    workspaces: Path, tmp_path: Path
) -> None:
    mine = tmp_path / "mine.py"
    mine.write_text("def two_sum(n, t): return (0, 1)\n", encoding="utf-8")

    code, output = solve(workspaces, TWO_SUM, "--source", str(mine), "--reference")

    assert code == 2
    assert "pick one" in output


def test_half_a_complexity_claim_is_refused_before_anything_is_provisioned(
    workspaces: Path,
) -> None:
    """A claim about one axis cannot disagree with an expectation about two, and
    checking it before the attempt starts means a typo does not leave a
    workspace behind.
    """
    code, output = solve(workspaces, TWO_SUM, "--reference", "--time", "O(n)")

    assert code == 2
    assert "go together" in output
    assert not workspaces.exists()


# --- the disk --------------------------------------------------------------


def test_a_graded_attempt_leaves_no_workspace_behind(workspaces: Path) -> None:
    """§8.1 ties workspace lifetime to an active attempt, so a completed one
    takes its directory with it — otherwise every kata run would leak a
    directory into the cache.
    """
    solve(workspaces, TWO_SUM, "--reference")

    assert list(workspaces.iterdir()) == []


def test_a_failed_attempt_also_leaves_no_workspace_behind(
    workspaces: Path,
) -> None:
    """A wrong answer is a *finished* attempt. Only an attempt that could not be
    graded at all keeps its directory, for inspection.
    """
    solve(workspaces, TWO_SUM)

    assert list(workspaces.iterdir()) == []


def test_it_solves_from_a_content_root_it_is_pointed_at(
    workspaces: Path, tmp_path: Path
) -> None:
    """`--content-root` has to reach the provisioner as well as the repository:
    the repository loads the exercise and the provisioner copies its files in.
    A root that reached only one would load from here and provision from there.
    """
    library = tmp_path / "content"
    library.mkdir()
    (library / "katas").mkdir()
    _copy_tree(content_root() / "katas" / "two-sum", library / "katas" / "two-sum")

    result = runner.invoke(
        app,
        [
            "solve",
            TWO_SUM,
            "--reference",
            "--content-root",
            str(library),
            "--workspace-root",
            str(workspaces),
            "--no-prompt",
        ],
    )

    assert result.exit_code == 0, result.output


def _copy_tree(source: Path, destination: Path) -> None:
    """A two-line copy rather than `shutil.copytree`, so this file does not
    import `shutil` only to move five files.
    """
    destination.mkdir(parents=True)
    for path in source.iterdir():
        if path.is_file():
            (destination / path.name).write_bytes(path.read_bytes())
