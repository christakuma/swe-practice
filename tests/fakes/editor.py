"""An editor that records what it was asked to open, and can refuse.

The second implementation of `EditorLauncher` (PLAN.md §13), and the one that
makes own-editor mode testable at all: the real one starts a GUI program and
does not wait for it, so a test driving it for real would either need an editor
installed or would prove nothing about the use case around it.

**Refusing is the case worth having a double for.** `EditorLauncher` returns the
problem rather than raising it, because a machine with no `code` on its PATH
still gets the path and the reason — and that branch is the whole reason the
`RevealedFile` DTO has three fields. `FakeEditorLauncher(problem=...)` is how a
test reaches it without unsetting an environment variable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["FakeEditorLauncher"]


class FakeEditorLauncher:
    """Satisfies `practice.domain.ports.EditorLauncher` and opens nothing."""

    def __init__(self, problem: str | None = None) -> None:
        #: What `reveal` answers with. `None` is a launch that worked; a sentence
        #: is one that did not, in the shape the real adapter returns.
        self.problem = problem
        #: Every path it was asked to open, in order. A list rather than a flag,
        #: because the question a test asks is *which* file -- a reveal that
        #: opened the tests or the stub of a different attempt would set a flag
        #: just as happily.
        self.revealed: list[Path] = []

    def reveal(self, path: Path) -> str | None:
        self.revealed.append(path)
        return self.problem
