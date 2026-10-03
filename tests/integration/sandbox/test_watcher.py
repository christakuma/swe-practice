"""The real file watcher, against real saves on a real directory.

The fake in `tests/fakes/watcher.py` is what makes the use case testable; this
is what makes the fake evidence of anything. Four claims, and three of them are
about what the watcher must *not* report:

* a write to the file is a change;
* a write to a sibling is not — the grading pass writes five of them into the
  same directory, and a watcher that reported those would re-grade its own
  output forever;
* a **rename over** the file is a change, which is how editors actually save;
* a tick arrives when nothing happens at all, which is how the web layer
  discovers a reader that has gone away.

**Every test bounds its own wait.** `changes` never returns on its own — the
real one only leaves through cancellation — so each of these takes what it needs
and cancels, with `asyncio.timeout` as the thing that fails rather than hangs.
A watcher test with no timeout is a suite that stops instead of failing.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Final

import pytest

from practice.adapters.sandbox.watcher import TICK_SECONDS, WatchfilesFileWatcher

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: How long a real save is given to be noticed. Generous for the same reason the
#: editor suite's is: a flaky integration test is worse than a slow one.
_PATIENCE: Final = 20.0

#: Short enough that the tick test does not take fifteen seconds. The adapter's
#: real default is `TICK_SECONDS`, which a test here asserts is the sane one.
_FAST_TICK: Final = 0.2


async def _first(
    watcher: WatchfilesFileWatcher, path: Path, saves: Callable[[], None]
) -> list[bool]:
    """Everything reported until the first `True`, with the writes interleaved.

    The writing happens *after* the watch has started, which is the whole
    ordering this has to get right: a file written before `awatch` is listening
    produces no event, and a test that wrote first would pass by timing out into
    a tick it mistook for silence.
    """
    reported: list[bool] = []
    async with asyncio.timeout(_PATIENCE):
        changes = watcher.changes(path)
        started = False
        async for changed in changes:
            if not started:
                # The first tick means the watcher is up; only now is a write
                # guaranteed to be seen.
                started = True
                await asyncio.to_thread(saves)
                continue
            reported.append(changed)
            if changed:
                break
        await changes.aclose()
    return reported


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A directory with the solver's file in it, and the grader's litter."""
    directory = tmp_path / "repo"
    directory.mkdir()
    (directory / "stub.py").write_text("def two_sum():\n    ...\n", encoding="utf-8")
    (directory / "tests.py").write_text("", encoding="utf-8")
    return directory


@pytest.mark.parametrize("tick_seconds", [_FAST_TICK])
def test_a_write_to_the_file_is_reported(repo: Path, tick_seconds: float) -> None:
    target = repo / "stub.py"

    def save() -> None:
        target.write_text("def two_sum():\n    return (0, 1)\n", encoding="utf-8")

    reported = asyncio.run(_first(WatchfilesFileWatcher(tick_seconds), target, save))

    assert reported[-1] is True


def test_a_rename_over_the_file_is_reported(repo: Path) -> None:
    """How editors actually save, and the reason the adapter watches the
    *directory* rather than the file: the inode a file watch was given stops
    being the file the solver is editing after the first save, and the symptom
    is a watcher that works exactly once.
    """
    target = repo / "stub.py"

    def save() -> None:
        scratch = repo / "stub.py.tmp"
        scratch.write_text("def two_sum():\n    return (1, 2)\n", encoding="utf-8")
        scratch.replace(target)

    reported = asyncio.run(_first(WatchfilesFileWatcher(_FAST_TICK), target, save))

    assert reported[-1] is True


def test_a_write_to_a_sibling_is_not_reported(repo: Path) -> None:
    """The grading pass writes `solution.py`, `conftest.py`, `pytest.ini`,
    `practice_report.py` and `report.json` into this directory. A watcher that
    reported them would re-grade on its own output, forever, as fast as pytest
    can start.
    """
    target = repo / "stub.py"

    def save_the_wrong_file() -> None:
        (repo / "report.json").write_text("{}", encoding="utf-8")
        (repo / "solution.py").write_text("x = 1\n", encoding="utf-8")
        # And then the real one, so this test ends rather than times out: what
        # it asserts is that nothing was reported *before* it.
        target.write_text("def two_sum():\n    return (0, 1)\n", encoding="utf-8")

    reported = asyncio.run(
        _first(WatchfilesFileWatcher(_FAST_TICK), target, save_the_wrong_file)
    )

    assert reported == [True]


def test_it_ticks_when_nothing_happens(repo: Path) -> None:
    """The `False` the port promises, which is what lets a web layer notice that
    the browser holding its stream open has gone.
    """

    async def collect() -> list[bool]:
        reported: list[bool] = []
        async with asyncio.timeout(_PATIENCE):
            changes = WatchfilesFileWatcher(_FAST_TICK).changes(repo / "stub.py")
            async for changed in changes:
                reported.append(changed)
                if len(reported) == 2:
                    break
            await changes.aclose()
        return reported

    assert asyncio.run(collect()) == [False, False]


def test_the_default_tick_is_long_enough_to_cost_nothing() -> None:
    """An idle tab wakes up four times a minute, not four times a second. The
    number is in the adapter rather than here, and this is the floor under it.
    """
    assert TICK_SECONDS >= 5.0
