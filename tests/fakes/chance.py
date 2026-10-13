"""A `Chooser` that is not left to chance.

Picks by position, so a test can say *which* version a "random" start lands on
and assert on what it was offered. The default is the last option, because the
first is always the standard version and a fake that picked it would make
"random" indistinguishable from not choosing at all.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.domain.ids import ExerciseId

__all__ = ["FixedChooser"]


class FixedChooser:
    """Satisfies `practice.domain.ports.Chooser`, and remembers what it saw."""

    def __init__(self, index: int = -1) -> None:
        self.index = index
        self.offered: list[tuple[ExerciseId, ...]] = []

    def choose(self, options: Sequence[ExerciseId]) -> ExerciseId:
        self.offered.append(tuple(options))
        return options[self.index]
