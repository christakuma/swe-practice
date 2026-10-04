"""One SQL drill, driven the whole way through the CLI, as a person would.

The third kind's e2e layer, and the half of Phase 14's exit criteria that no
other suite can make: **the drill kind is reachable through the shipped product,
not merely implemented behind it.** Phase 13's lesson, stated in ADR 0018 — "a
scheduler nobody can select is written rather than shipped" — applies to an
exercise kind at least as much.

Two tests, for the reason `test_solve_a_kata.py` gives: an e2e layer that grows
is an e2e layer that becomes the slowest and least informative part of the
suite. Everything else about drills is asserted one layer down, where it is
milliseconds instead of a process.

What is deliberately *not* duplicated from the kata journey: `gc` finding
nothing afterwards. That is a property of `solve` and the provisioner, which a
drill shares with a kata unchanged — the drill engine never writes a file, so
there is strictly less to leak.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from practice.interface.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

DRILL = "sql/one-row-per-customer"

#: What a solver would arrive at. The `LEFT JOIN` and `COUNT(o.id)` are the two
#: things the exercise is about, and both are wrong in the stub by being absent.
SOLVED = """\
SELECT c.name,
       COUNT(o.id) AS orders
  FROM customers c
  LEFT JOIN orders o ON o.customer_id = c.id
 GROUP BY c.id
 ORDER BY c.name;
"""

runner = CliRunner()


@pytest.fixture
def workspaces(tmp_path: Path) -> Path:
    return tmp_path / "ws"


def test_a_drill_goes_from_failing_to_passing(workspaces: Path, tmp_path: Path) -> None:
    """The loop the product is, for the kind that had no engine two commits ago.

    The first invocation submits the stub, which is comments — so SQLite runs no
    statements, `answer-ran` is the only thing that could pass, and every
    declared check fails against a database nothing touched. That is the verdict
    a solver sees before they start, and it has to be a `FAIL` rather than a
    traceback.
    """
    first = runner.invoke(
        app, ["solve", DRILL, "--no-prompt", "--workspace-root", str(workspaces)]
    )

    assert first.exit_code == 1, first.output
    assert "FAIL" in first.output

    mine = tmp_path / "answer.sql"
    mine.write_text(SOLVED, encoding="utf-8", newline="\n")

    second = runner.invoke(
        app,
        [
            "solve",
            DRILL,
            "--no-prompt",
            "--source",
            str(mine),
            "--workspace-root",
            str(workspaces),
        ],
    )

    assert second.exit_code == 0, second.output
    assert second.output.rstrip().endswith("PASS")


def test_the_schema_is_in_the_workspace_for_the_solver_to_read(
    workspaces: Path,
) -> None:
    """The one thing about a drill's workspace that is not true of a kata's.

    `seed.sql` is copied in deliberately: the schema is the question, not the
    answer, and a drill whose column names could not be read would be a riddle.
    `solution.sql` is *not* copied in, which is the answer key staying outside
    the exam — and both halves are asserted here because this is the only suite
    that provisions a real drill workspace through the real command.

    Through `start` rather than `solve`, because `solve` disposes of the
    workspace on its way out (§8.1 ties a workspace's lifetime to an active
    attempt) — so there would be nothing left to look at. That is the command
    whose whole job is to leave an attempt open.
    """
    started = runner.invoke(app, ["start", DRILL, "--workspace-root", str(workspaces)])

    assert started.exit_code == 0, started.output

    repos = list(workspaces.glob("*/repo"))
    assert len(repos) == 1, [str(path) for path in workspaces.glob("*")]
    present = {path.name for path in repos[0].iterdir()}

    assert "seed.sql" in present
    assert "stub.sql" in present
    assert "solution.sql" not in present
