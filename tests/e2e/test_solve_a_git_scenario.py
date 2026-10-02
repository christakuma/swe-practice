"""One git scenario, driven the whole way through the CLI, as a person would.

The other half of PLAN.md §9's last testing layer, and the half the project exists
for. It overlaps `tests/integration/test_cli_solve_scenario.py` on purpose and is not
a duplicate: that suite checks each behaviour of one command in isolation, and this
one checks that the *journey* works and that the commands compose.

Two tests, because an e2e layer that grows is an e2e layer that becomes the slowest
and least informative part of the suite. Anything that can be asserted one layer down
belongs one layer down — so what is left here is the one thing that cannot be: **two
wrong answers and one right one, graded through the shipped command, coming apart on
exactly the checks that distinguish them while agreeing on the content.**

That is PLAN.md §1 in a single assertion, and it is the sentence the whole
architecture was arranged to make true.
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

#: What a correct answer does. Deliberately *not* the exercise's own
#: `solution.cmds` -- the point of grading the end state is that the tool never
#: punishes a correct answer it did not anticipate, and a journey test that replayed
#: the answer key would be the one place that assumption went untested. Three
#: commands, no inspection, `-m` instead of `--no-edit`: nothing like the reference
#: and correct all the same.
MINE = """\
git revert HEAD --no-edit
git log --oneline --decorate --all
git push origin main
"""

#: The tempting wrong answer: same tree, rewritten history.
RESET = "git reset --hard HEAD~1\ngit push --force origin main\n"

runner = CliRunner()


@pytest.fixture
def workspaces(tmp_path: Path) -> Path:
    """Never the user cache: a test run must not collide with an open session."""
    return tmp_path / "ws"


def solve(workspaces: Path, *arguments: str) -> tuple[int, str]:
    result = runner.invoke(
        app,
        [
            "solve",
            REVERT,
            *arguments,
            "--workspace-root",
            str(workspaces),
            "--no-prompt",
        ],
    )
    return result.exit_code, result.output


def test_two_answers_with_the_same_tree_are_graded_differently(
    workspaces: Path, tmp_path: Path
) -> None:
    """The project's thesis, end to end through the shipped command.

    Both answers leave `main` with byte-identical content -- `build.sh` finds
    `parse_line` again either way -- so `content-restored` passes for both. One of
    them rewrote history a teammate had already pulled, and `history-preserved` is
    what notices. A tool grading on file content accepts both; a tool matching
    command text would have to guess which of two dozen correct phrasings to allow.

    Written against an answer that is *not* the exercise's reference solution, so
    "it does not punish a correct answer it did not anticipate" is tested rather
    than assumed.
    """
    mine = tmp_path / "mine.cmds"
    mine.write_text(MINE, encoding="utf-8")
    naive = tmp_path / "naive.cmds"
    naive.write_text(RESET, encoding="utf-8")

    right_code, right = solve(workspaces, "--commands", str(mine))
    wrong_code, wrong = solve(workspaces, "--commands", str(naive))

    # Both get the content right.
    content = "The committed tree matches the state before the bad commit"
    assert f"  ok   {content}" in right
    assert f"  ok   {content}" in wrong

    # They come apart on ancestry, and only on ancestry.
    history = "The bad commit is still reachable"
    assert f"  ok   {history}" in right
    assert f"  FAIL {history}" in wrong

    assert right_code == 0, right
    assert wrong_code == 1, wrong
    assert right.rstrip().endswith("PASS")


def test_gc_finds_nothing_after_a_scenario_has_been_solved(workspaces: Path) -> None:
    """The two commands agreeing about the same directory.

    More load-bearing here than for a kata: a scenario's workspace holds a real
    repository, bare remotes and a few dozen loose git objects, and disposing of it
    is the operation PLAN.md's sandbox notes single out as the Windows papercut --
    git marks loose objects read-only and Windows honours that against deletion. A
    leak would show up here as a workspace `gc` can see and nothing can collect,
    which is precisely the state §8.1 is arranged to avoid.
    """
    solve(workspaces, "--reference")

    collected = runner.invoke(app, ["gc", "--workspace-root", str(workspaces)])

    assert collected.exit_code == 0, collected.output
    assert "No workspaces." in collected.output
    assert str(content_root()) not in collected.output
