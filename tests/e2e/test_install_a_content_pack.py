"""A pack, exported and installed and then solved from, through the CLI.

**The only suite that can hold Phase 16's second exit clause**, and the reason
this file exists rather than more cases in `tests/content/test_pack.py`. That
file proves an installed root *loads* — the curriculum is intact, every byte
matches, `validate_library` passes. None of that says an exercise in it can be
attempted, because loading goes through `ContentRepository` and attempting does
not: the sandbox copies a fixture, a stub or a `seed.sql` out of a content root
by path, and a pack that installed a library the provisioner could not read
would pass every other test in the phase.

So the journey here is the whole of it: export the shipped library to a file,
install that file somewhere else, and solve an exercise out of the result with
`--content-root` pointing at it and nothing pointing at `content/`.

Two tests, for the reason `test_solve_a_sql_drill.py` gives: an e2e layer that
grows is the slowest and least informative part of the suite. The second one is
here only because a git scenario is the kind whose files the pack handles
*differently* — a fixture is bash that gets executed, and its commit hashes are
pinned, so it is the one case where a pack mangling a byte would show up as
something other than a missing file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from practice.interface.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

KATA = "katas/two-sum"
SCENARIO = "git/revert-a-pushed-commit"

runner = CliRunner()


@pytest.fixture
def installed(tmp_path: Path) -> Path:
    """The shipped library, exported to a pack and installed somewhere else.

    Both steps through the CLI rather than through `write_pack`/`install_pack`,
    because the claim is about the product: a user types two commands and ends
    up with a library.
    """
    archive = tmp_path / "library.practicepack"
    export = runner.invoke(app, ["pack", "--out", str(archive)])
    assert export.exit_code == 0, export.output

    root = tmp_path / "root"
    install = runner.invoke(
        app, ["pack", "--install", str(archive), "--into", str(root)]
    )
    assert install.exit_code == 0, install.output
    return root


def test_a_kata_from_an_installed_pack_goes_from_failing_to_passing(
    installed: Path, tmp_path: Path
) -> None:
    """The clause: an installed pack is a library you can be graded against.

    The stub fails and the solution passes, exactly as against `content/` — and
    the only thing different about this run is where the `tests.py` came from.
    A pack that dropped it, or that re-encoded it, fails here and nowhere else.

    **Both files come out of the installed root**, which is deliberate and is
    two assertions for the price of one: the answer is the library's own
    reference rather than a copy pasted in here, so this also says the pack
    carried `solution.py` — the file PLAN.md §5.3 keeps *out* of the workspace
    and which therefore reaches a workspace by no other route.
    """
    workspaces = tmp_path / "ws"

    first = runner.invoke(
        app,
        [
            "solve",
            KATA,
            "--no-prompt",
            "--content-root",
            str(installed),
            "--workspace-root",
            str(workspaces),
        ],
    )

    assert first.exit_code == 1, first.output
    assert "FAIL" in first.output

    second = runner.invoke(
        app,
        [
            "solve",
            KATA,
            "--source",
            str(installed / KATA / "solution.py"),
            "--no-prompt",
            "--content-root",
            str(installed),
            "--workspace-root",
            str(workspaces),
        ],
    )

    assert second.exit_code == 0, second.output
    assert "PASS" in second.output


def test_a_scenario_fixture_still_builds_the_history_it_is_pinned_to(
    installed: Path, tmp_path: Path
) -> None:
    """The case where a mangled byte shows up as something other than absence.

    A fixture is bash that is executed, and `fixtures.lock` pins the commit
    hashes it produces, so a pack that converted its line endings in transit
    would build a *different and valid-looking* history. Grading the reference
    solution out of the installed root is what notices: the checks are written
    against the pinned history, so they fail if the fixture built another one.
    """
    commands = installed / SCENARIO / "solution.cmds"

    result = runner.invoke(
        app,
        [
            "solve",
            SCENARIO,
            "--commands",
            str(commands),
            "--no-prompt",
            "--content-root",
            str(installed),
            "--workspace-root",
            str(tmp_path / "ws"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "PASS" in result.output
