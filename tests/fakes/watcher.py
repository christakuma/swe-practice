"""A file watcher that yields a script instead of watching anything.

The second implementation of `FileWatcher` (PLAN.md §13), and the one that makes
*grade on every save* a unit test. The alternative is to write a real file and
hope the real watcher notices before the test's patience runs out, which is how
you get a suite that fails once a fortnight on CI and never locally.

**The script is arranged rather than signalled.** A fake that had to be poked
from another task would need the test to coordinate two coroutines, which is more
machinery than the thing being tested — and the thing being tested is what the
use case *does* with a save, not how it waits for one. So a test says "two saves
and a tick", drains the stream, and asserts on what came out.

**It is a queue, so a test may add to it from inside the loop.** That is what
makes "save, see the verdict, save something different" expressible, which is
the sequence a solver actually produces. It is also a trap worth naming: a test
that appends on *every* draft never ends, and the symptom is a unit test that
hangs rather than fails. Add the next save under a condition.

**It ends, and the real one does not.** `WatchfilesFileWatcher.changes` only
leaves through cancellation; this one runs out of script. That is the one place
the fake is deliberately unlike the adapter, and it is what lets a test use a
plain `async for` without a timeout around it. The use case cannot tell the
difference: an async generator that returns is the same thing as one that is
cancelled, from the inside of a `for` loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path

__all__ = ["FakeFileWatcher"]


class FakeFileWatcher:
    """Satisfies `practice.domain.ports.FileWatcher` from a list."""

    def __init__(self, script: list[bool] | None = None) -> None:
        #: What `changes` will yield, in order. `True` is a save, `False` a tick.
        self.script: list[bool] = list(script or [])
        #: Every path it was asked to watch. A list rather than a flag, because
        #: the question worth asking is *which* file -- a stream watching the
        #: tests, or another attempt's stub, would set a flag just as happily.
        self.watched: list[Path] = []

    def saves(self, count: int = 1) -> FakeFileWatcher:
        """Script `count` saves. Chainable, so a test reads as a sequence."""
        self.script.extend([True] * count)
        return self

    def ticks(self, count: int = 1) -> FakeFileWatcher:
        """Script `count` periodic wake-ups with nothing to report."""
        self.script.extend([False] * count)
        return self

    async def changes(self, path: Path) -> AsyncGenerator[bool]:
        self.watched.append(path)
        while self.script:
            yield self.script.pop(0)
