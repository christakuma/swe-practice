"""One attempt under interview conditions, start to verdict. Phase 15 as a journey.

The fifth e2e file, and it earns its place the way the others do: there is
exactly one thing here that cannot be asserted a layer down.
`tests/integration/test_cli_lifecycle.py` checks each command's own output and
`tests/unit/` checks each rule in isolation. Neither can check what this does —
that **the mode chosen in the first invocation is still the mode the fourth one
grades under**, with no flag repeated anywhere, and that an interview attempt is
solvable to a PASS without the two affordances it withdraws.

That is the claim interview mode rests on. A mode read from a flag on each
invocation would pass every unit test in the phase and fail here, because
`resume` and `submit` are never told about it — which is also exactly how the
command budget was shown to belong to the attempt in Phase 6.

One test, because an e2e layer that grows is an e2e layer that becomes the
slowest and least informative part of the suite. The hint refusal is *not* here
and the reason is worth stating: the only surface that reveals a hint is the
browser, whose endpoints are behind the app's own origin guard, and a client
built here to satisfy that guard would be a second, worse copy of
`tests/web/conftest.py`. It is asserted there, against the real app
(`test_the_hint_endpoint_refuses_an_interview_outright`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from practice.interface.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

TWO_SUM = "katas/two-sum"

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
def storage(tmp_path: Path) -> tuple[Path, Path]:
    """Never the user's own: a test run must not collide with an open session."""
    return tmp_path / "ws", tmp_path / "practice.db"


def invoke(storage: tuple[Path, Path], *arguments: str) -> tuple[int, str]:
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


def test_an_interview_is_sat_and_passed_without_its_rules_being_repeated(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    """Start under interview rules, be refused the workspace, write an answer of
    your own, be refused a hint, and submit it — four invocations, one `--interview`.

    The answer goes in a file the test writes rather than into the workspace's
    stub, which is not a convenience: the workspace path was never printed, so a
    solver following the instruction on screen *has* no path to write to. This is
    the journey that would be impossible if the third clause were cosmetic.
    """
    mine = tmp_path / "mine.py"
    mine.write_text(SOLVED, encoding="utf-8", newline="\n")
    workspaces, _ = storage

    started, start_output = invoke(
        storage, "start", TWO_SUM, "--no-prompt", "--interview"
    )
    attempt = attempt_id_from(start_output)

    assert started == 0, start_output
    # The rules are stated once, where they were chosen.
    assert "no hints" in start_output
    assert "15 minute limit" in start_output
    # And the affordance is withdrawn: no workspace path, so nothing to peek in.
    assert str(workspaces) not in start_output
    assert "a file of your own" in start_output

    # Three further invocations, none of them told anything about the mode.
    resumed, resume_output = invoke(storage, "resume", attempt)
    graded, verdict = invoke(storage, "submit", attempt, "--source", str(mine))

    assert [resumed, graded] == [0, 0], verdict

    # The mode survived into the second process, and the clock with it.
    assert "no hints" in resume_output
    assert "minutes left" in resume_output
    assert str(workspaces) not in resume_output

    # And the answer was graded on its merits, which is the thing interview mode
    # must not interfere with. `PASS, with advisories` rather than a bare PASS:
    # no complexity was declared, and that advisory is the same one a practice
    # submission without `--time`/`--space` gets. Interview mode has no opinion
    # about it, which is the point of asserting the whole line.
    assert "PASS, with advisories" in verdict
    assert "You declared the cost of your solution." in verdict

    # One attempt in the history, still an interview.
    _, history = invoke(storage, "attempts", "--exercise", TWO_SUM)
    assert f"1 attempt at {TWO_SUM}." in history
    assert "no hints" in history
