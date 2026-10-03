"""Noticing that the solver saved their file.

Satisfies `practice.domain.ports.FileWatcher` structurally (ADR 0002), over
`watchfiles` — the one dependency declared in Phase 0 that nothing had used
until now (PLAN.md §2: *"for 'solve it in my own editor' mode"*).

**It watches the directory and filters, rather than watching the file.** That is
the whole content of this module and it is not an optimisation. Editors do not
write files, they replace them: VS Code, vim and `write`-style tools all save by
writing a temporary file and renaming it over the target, so the inode the
watcher was given stops being the file the solver is editing after the first
save. A directory watch sees the rename; a file watch sees one modification and
then nothing ever again — which is the version of this bug that looks like it
works.

**The filter is positive, naming the one file.** The grading pass writes five
other files into the same directory — `solution.py`, `conftest.py`,
`pytest.ini`, `practice_report.py`, `report.json` (`kata.mechanism_files`) — so
a directory watch that reported everything would re-grade on its own output,
forever, at whatever rate pytest can start. Excluding the known five would be
the same rule written the fragile way round: a sixth would restart the loop.

**The periodic tick is part of the contract, not a detail.** `yield_on_timeout`
makes `awatch` wake up with an empty batch every `_TICK_MS`, and the `False` this
yields for it is how the web layer discovers a browser that has gone away — see
`FileWatcher` in `domain/ports.py`. Without it, an abandoned stream would sit in
`awatch` forever holding a watcher.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

from watchfiles import awatch

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from watchfiles.main import Change

__all__ = ["TICK_SECONDS", "WatchfilesFileWatcher"]

#: How often a stream with nothing to report wakes up. Fifteen seconds: long
#: enough that an idle tab costs nothing, short enough that a closed one is
#: noticed and its watcher released while the solver is still in the session.
TICK_SECONDS: Final = 15.0

_MILLISECONDS: Final = 1000


class WatchfilesFileWatcher:
    """Satisfies `practice.domain.ports.FileWatcher` over one directory watch.

    Holds no state about any one file — the path is an argument — so the
    composition root builds exactly one, like the pytest runner and the editor
    launcher.
    """

    __slots__ = ("_tick_seconds",)

    def __init__(self, tick_seconds: float = TICK_SECONDS) -> None:
        self._tick_seconds = tick_seconds

    async def changes(self, path: Path) -> AsyncGenerator[bool]:
        """`True` when `path` was written, `False` on a tick. Never returns.

        Typed as the generator it is rather than as the port's `AsyncIterator`,
        which is the narrower claim and a true one: a caller that wants to stop
        early -- a test, as it happens -- can `aclose()` it, and the port stays
        the weakest thing its callers actually need.

        Cancellation is the only way out, which is what a caller holding an HTTP
        connection wants: `awatch` sets its stop event when the task it is
        running in is cancelled, so closing the browser tab releases the
        watcher through the normal path rather than through a flag somebody has
        to remember to set.
        """
        target = path.name

        def is_the_file(change: Change, changed: str) -> bool:
            del change  # created, modified or deleted: a save can be any of them
            return Path(changed).name == target

        async for batch in awatch(
            path.parent,
            watch_filter=is_the_file,
            rust_timeout=int(self._tick_seconds * _MILLISECONDS),
            yield_on_timeout=True,
        ):
            yield bool(batch)
