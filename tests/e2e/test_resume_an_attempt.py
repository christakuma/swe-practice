"""One attempt, across four processes. PLAN.md's Phase 6 exit criterion as a journey.

The third e2e file, and it earns its place the way the other two do: there is exactly
one thing here that cannot be asserted a layer down. `tests/integration/test_cli_
lifecycle.py` checks each command's own behaviour, and
`tests/integration/persistence/` checks that a repository hands back what it stored.
Neither of them can check what this does — that **four separate `practice`
invocations share one repository, one event log and one budget**, and that the
verdict at the end is derived from all of it.

Until this phase the CLI's own docstring said an attempt could not outlive the
process that started it, and `solve` was the only shape a session could take. The
assertion that proves otherwise is the advisory: `command_used` reads the *attempt's*
command log, not the repository, so "you inspected the repository before changing it"
passing means the `git log` run by the second process was still in the log when the
fourth one graded.

Two tests, because an e2e layer that grows is an e2e layer that becomes the slowest
and least informative part of the suite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from practice.interface.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

REVERT = "git/revert-a-pushed-commit"

runner = CliRunner()


@pytest.fixture
def storage(tmp_path: Path) -> tuple[Path, Path]:
    """Never the user's own: a test run must not collide with an open session, and
    must not write into a real attempt history.
    """
    return tmp_path / "ws", tmp_path / "practice.db"


def invoke(storage: tuple[Path, Path], *arguments: str) -> tuple[int, str]:
    """One `practice` invocation. Each call is its own process, as far as state goes:
    nothing is carried over in memory, only the two paths.
    """
    workspaces, database = storage
    result = runner.invoke(
        app,
        [
            *arguments,
            "--workspace-root",
            str(workspaces),
            "--database",
            str(database),
        ],
    )
    return result.exit_code, result.output


def attempt_id_from(output: str) -> str:
    for line in output.splitlines():
        if "attempt " in line:
            return line.split("attempt ", 1)[1].strip()
    raise AssertionError(f"no attempt id in:\n{output}")


def test_an_attempt_is_solved_across_four_invocations(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    """Start, look, fix, submit — four processes, one attempt.

    Deliberately *not* the exercise's own `solution.cmds`, and deliberately split
    across two `resume` calls at a point where the second half depends on the first:
    `git revert HEAD` means something different if the `git log` never happened and
    the repository was rebuilt in between.
    """
    look = tmp_path / "look.cmds"
    look.write_text("git log --oneline --decorate --all\n", encoding="utf-8")
    fix = tmp_path / "fix.cmds"
    fix.write_text(
        "git revert HEAD --no-edit\ngit push origin main\n", encoding="utf-8"
    )

    started, start_output = invoke(storage, "start", REVERT, "--no-prompt")
    attempt = attempt_id_from(start_output)
    looked, _ = invoke(storage, "resume", attempt, "-c", str(look))
    fixed, _ = invoke(storage, "resume", attempt, "-c", str(fix))
    graded, verdict = invoke(storage, "submit", attempt)

    assert [started, looked, fixed, graded] == [0, 0, 0, 0], verdict

    # The repository was graded as the third process left it.
    assert (
        "  ok   The committed tree matches the state before the bad commit" in verdict
    )
    assert "  ok   The bad commit is still reachable" in verdict

    # And the *log* survived all four: this advisory reads the attempt's command
    # history, and the command that satisfies it ran two processes ago.
    assert "  ok   You inspected the repository before changing it" in verdict
    assert verdict.rstrip().endswith("PASS")

    # One attempt in the history, not four.
    _, history = invoke(storage, "attempts", "--exercise", REVERT)
    assert f"1 attempt at {REVERT}." in history
    assert "3/25 commands" in history


def test_an_abandoned_attempt_frees_its_workspace_and_gc_agrees(
    storage: tuple[Path, Path],
) -> None:
    """The other half of resume-or-abandon, and the three commands agreeing.

    More load-bearing here than for a kata: a scenario's workspace holds a real
    repository, bare remotes and a few dozen loose git objects that git has marked
    read-only — the Windows papercut PLAN.md's sandbox notes single out. A leak would
    show up as a workspace `gc` can see and nothing can collect, which is precisely
    the state §8.1 is arranged to avoid.
    """
    _, start_output = invoke(storage, "start", REVERT, "--no-prompt")
    attempt = attempt_id_from(start_output)
    assert "1 in use, 0 orphans" in invoke(storage, "gc")[1]

    code, output = invoke(storage, "abandon", attempt)

    assert code == 0, output
    assert "No open attempts." in invoke(storage, "attempts")[1]
    assert "No workspaces." in invoke(storage, "gc")[1]
    # The row stays, marked: the history is the point.
    assert "abandoned" in invoke(storage, "attempts", "--exercise", REVERT)[1]
