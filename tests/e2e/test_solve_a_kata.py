"""One kata, driven the whole way through the CLI, as a person would.

PLAN.md §9's last testing layer. It overlaps `tests/integration/test_cli_solve.py`
on purpose and is not a duplicate of it: that suite checks each behaviour of one
command in isolation — exit codes, refusals, flags — and this one checks that
the *journey* works and that the commands compose. Fail on the stub, fix it,
pass, and have `practice gc` agree that nothing was left behind.

The git scenario half lives in `test_solve_a_git_scenario.py`, which lands with
the engine that can grade one.

Two tests, because an e2e layer that grows is an e2e layer that becomes the
slowest and least informative part of the suite. Anything that can be asserted
one layer down belongs one layer down.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from practice.interface.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

TWO_SUM = "katas/two-sum"

#: What a solver would arrive at: the one-pass dict, written out longhand.
SOLVED = """\
def two_sum(numbers, target):
    seen = {}
    for index, value in enumerate(numbers):
        complement = target - value
        if complement in seen:
            return (seen[complement], index)
        seen[value] = index
    raise ValueError("no pair of values adds up to the target")
"""

runner = CliRunner()


@pytest.fixture
def workspaces(tmp_path: Path) -> Path:
    return tmp_path / "ws"


def test_a_kata_goes_from_failing_to_passing(workspaces: Path, tmp_path: Path) -> None:
    """The loop the product is: run it, see what is wrong, fix it, run it again.

    The two invocations share a workspace *root* and nothing else — each starts
    its own attempt, provisions its own directory and disposes of it — which is
    the Phase 4 shape: an attempt cannot outlive the process that started it
    until the attempt table lands in Phase 6.
    """
    first = runner.invoke(
        app, ["solve", TWO_SUM, "--no-prompt", "--workspace-root", str(workspaces)]
    )

    assert first.exit_code == 1, first.output
    assert "FAIL" in first.output

    mine = tmp_path / "two_sum.py"
    mine.write_text(SOLVED, encoding="utf-8")

    second = runner.invoke(
        app,
        [
            "solve",
            TWO_SUM,
            "--no-prompt",
            "--source",
            str(mine),
            "--time",
            "O(n)",
            "--space",
            "O(n)",
            "--workspace-root",
            str(workspaces),
        ],
    )

    assert second.exit_code == 0, second.output
    assert second.output.rstrip().endswith("PASS")


def test_gc_finds_nothing_after_a_kata_has_been_solved(workspaces: Path) -> None:
    """The two commands agreeing about the same directory.

    `solve` disposes of a completed attempt's workspace and `gc` reports what is
    left; a leak would show up here as a workspace `gc` can see and nothing can
    collect, which is precisely the state §8.1 is arranged to avoid.
    """
    runner.invoke(
        app,
        [
            "solve",
            TWO_SUM,
            "--reference",
            "--no-prompt",
            "--workspace-root",
            str(workspaces),
        ],
    )

    collected = runner.invoke(app, ["gc", "--workspace-root", str(workspaces)])

    assert collected.exit_code == 0, collected.output
    assert "No workspaces." in collected.output
