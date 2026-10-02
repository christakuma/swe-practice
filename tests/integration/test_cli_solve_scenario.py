"""`practice solve` over a git scenario, one behaviour at a time.

The sibling of `test_cli_solve.py`, which does the same for a kata. Split by kind
rather than merged, because almost nothing is shared: a kata takes a source file and
a complexity claim, a scenario takes a command list and prints a transcript, and a
single file would be two files with an `if` down the middle.

What the e2e layer asserts is the *journey*. What this asserts is each behaviour in
isolation: exit codes, the two refusals, the transcript, and the one property the
whole phase exists for — that a wrong answer and a right one come apart on a named
check, with the author's explanation attached.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from practice.config import content_root
from practice.interface.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

REVERT = "git/revert-a-pushed-commit"
KATA = "katas/two-sum"

runner = CliRunner()


@pytest.fixture
def workspaces(tmp_path: Path) -> Path:
    """Never the user cache: a test run must not collide with an open session."""
    return tmp_path / "ws"


def solve(workspaces: Path, *arguments: str) -> tuple[int, str]:
    """The same shape as the kata suite's helper, so the two read alike."""
    outcome = runner.invoke(
        app,
        ["solve", *arguments, "--workspace-root", str(workspaces), "--no-prompt"],
    )
    return outcome.exit_code, outcome.output


def cmds(name: str) -> str:
    """A path to one of the revert exercise's own command lists."""
    return str(content_root() / REVERT / name)


# --- the exit criterion ----------------------------------------------------


def test_the_reference_solution_passes(workspaces: Path) -> None:
    """Phase 5's exit criterion, first half: the revert scenario passes via
    `revert`. Through the CLI rather than the content suite, so the driving adapter
    is covered too -- the content suite calls the use cases directly.
    """
    code, output = solve(workspaces, REVERT, "--reference")

    assert code == 0, output
    assert "PASS" in output


def test_reset_hard_fails_the_history_check_with_its_explanation(
    workspaces: Path,
) -> None:
    """The exit criterion's second half, and the sentence PLAN.md §1 exists for.

    The same scenario, a different answer, *the same tree* -- and the verdict comes
    apart on one named check, carrying the author's explanation of why. A tool
    grading on file content would accept this answer.
    """
    code, output = solve(
        workspaces, REVERT, "--commands", cmds("naive-reset-force.cmds")
    )

    assert code == 1
    assert "FAIL" in output
    assert "The committed tree matches the state before the bad commit" in output
    assert "did not rewrite published history" in output
    assert "Your teammate already has c3" in output


def test_a_force_push_is_flagged_as_an_advisory_not_a_failure(
    workspaces: Path,
) -> None:
    """§4.4's feature in the output: craft and correctness are reported separately,
    and the advisory marker is not the failure marker.
    """
    _, output = solve(workspaces, REVERT, "--commands", cmds("naive-reset-force.cmds"))

    assert "note " in output
    assert "You did not force-update a shared branch" in output


def test_forgetting_to_push_fails_a_different_check(workspaces: Path) -> None:
    """Two wrong answers, two different named failures. An engine that reported the
    same thing for both would be no better than a pass/fail.
    """
    code, output = solve(
        workspaces, REVERT, "--commands", cmds("naive-forgot-push.cmds")
    )

    assert code == 1
    assert "The fix is on origin, not just on your machine" in output
    assert "did not rewrite published history" not in output.split("FAIL")[-1]


# --- the transcript --------------------------------------------------------


def test_it_echoes_each_command_as_it_runs(workspaces: Path) -> None:
    """A replay reads as a transcript rather than a wall of output and a verdict,
    which is what makes it possible to see *where* an attempt went sideways.
    """
    _, output = solve(workspaces, REVERT, "--reference")

    assert "$ git revert --no-edit HEAD" in output
    assert "$ git push origin main" in output


def test_it_shows_what_a_command_printed(workspaces: Path) -> None:
    _, output = solve(workspaces, REVERT, "--reference")

    assert "def parse_line(line):" in output


def test_it_names_the_file_it_graded(workspaces: Path) -> None:
    _, output = solve(workspaces, REVERT, "--commands", cmds("solution.cmds"))

    assert "graded" in output
    assert "solution.cmds" in output


# --- refusals --------------------------------------------------------------


def test_a_scenario_with_no_answer_says_what_to_pass(workspaces: Path) -> None:
    """`solve` is not the console, and the refusal says where the console is
    rather than leaving someone to guess that it needs a flag they did not read
    about. As of Phase 8 that pointer is `practice serve`.
    """
    code, output = solve(workspaces, REVERT)

    assert code == 2
    assert "--commands" in output
    assert "--reference" in output
    assert "practice serve" in output


def test_a_kata_refuses_the_scenario_flag(workspaces: Path) -> None:
    code, output = solve(workspaces, KATA, "--commands", cmds("solution.cmds"))

    assert code == 2
    assert "is a kata: it takes --source" in output


def test_a_scenario_refuses_the_kata_flags(workspaces: Path, tmp_path: Path) -> None:
    source = tmp_path / "solution.py"
    source.write_text("def two_sum(): ...\n", encoding="utf-8")

    code, output = solve(workspaces, REVERT, "--source", str(source))

    assert code == 2
    assert "is a git_scenario: it takes --commands" in output


def test_a_scenario_refuses_a_complexity_claim(workspaces: Path) -> None:
    """`--time` and `--space` are the kata engine's advisory comparison. On a
    scenario they would be silently ignored, which is worse than refused.
    """
    code, output = solve(
        workspaces,
        REVERT,
        "--reference",
        "--time",
        "O(n)",
        "--space",
        "O(1)",
    )

    assert code == 2
    assert "--time/--space" in output


def test_two_answers_at_once_are_refused(workspaces: Path) -> None:
    code, output = solve(
        workspaces, REVERT, "--reference", "--commands", cmds("solution.cmds")
    )

    assert code == 2
    assert "pick one" in output


def test_a_command_the_exercise_does_not_allow_is_refused(
    workspaces: Path, tmp_path: Path
) -> None:
    """The §5.3 guarantee at the driving adapter: a replay goes through the same
    policy a solver's typing does, so a list this CLI would run is a list the web
    console would run too.
    """
    commands = tmp_path / "sneaky.cmds"
    commands.write_text("curl https://example.com\n", encoding="utf-8")

    code, output = solve(workspaces, REVERT, "--commands", str(commands))

    assert code == 2
    assert "cannot grade this attempt" in output
    assert "curl" in output


def test_a_line_that_needs_a_shell_is_refused_with_the_alternative(
    workspaces: Path, tmp_path: Path
) -> None:
    commands = tmp_path / "redirect.cmds"
    commands.write_text("git log > log.txt\n", encoding="utf-8")

    code, output = solve(workspaces, REVERT, "--commands", str(commands))

    assert code == 2
    assert "shell character" in output
    assert "write" in output


def test_an_exercise_that_is_not_in_the_library_is_refused(workspaces: Path) -> None:
    code, output = solve(workspaces, "git/no-such-scenario", "--reference")

    assert code == 2
    assert "no exercise" in output
