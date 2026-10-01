"""The commit clock, which is a file because it has to outlive a process.

An integration test rather than a unit one: the whole point of `SandboxClock` is
that it is backed by a file in the workspace, so a version of these tests that
did not touch a filesystem would not be testing the thing that matters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.adapters.sandbox.env import FIXTURE_EPOCH, FIXTURE_STEP, SandboxClock

if TYPE_CHECKING:
    from pathlib import Path


def test_the_clock_starts_at_the_fixture_epoch(tmp_path: Path) -> None:
    clock = SandboxClock(tmp_path / "clock")
    clock.start()

    assert clock.read() == FIXTURE_EPOCH


def test_the_clock_advances_one_step_at_a_time(tmp_path: Path) -> None:
    clock = SandboxClock(tmp_path / "clock")
    clock.start()

    assert clock.tick() == FIXTURE_EPOCH + FIXTURE_STEP
    assert clock.tick() == FIXTURE_EPOCH + 2 * FIXTURE_STEP


def test_the_clock_survives_the_process_that_set_it(tmp_path: Path) -> None:
    """The reason it is a file and not an attribute (PLAN.md §6.1).

    The fixture advances it in a bash process that then exits, and a resumed
    attempt advances it in a Python process that did not provision the
    workspace. Neither can tell the other where the history got to except
    through the workspace.
    """
    path = tmp_path / "clock"
    SandboxClock(path).start()
    first = SandboxClock(path).tick()

    assert SandboxClock(path).read() == first


def test_a_missing_clock_reads_as_the_start(tmp_path: Path) -> None:
    """A fixture that made no commits never writes the file."""
    assert SandboxClock(tmp_path / "absent").read() == FIXTURE_EPOCH


def test_a_corrupt_clock_reads_as_the_start(tmp_path: Path) -> None:
    """A hand-edited clock is a reproducibility problem, not a reason to refuse
    to run the attempt — and the fallback is where the fixture would have begun.
    """
    path = tmp_path / "clock"
    path.write_text("not a number", encoding="utf-8")

    assert SandboxClock(path).read() == FIXTURE_EPOCH
