"""The `Chooser` port over `random.choice`.

One line of behaviour and a module to itself, for the reason `ids.py` gives
about `uuid4`: the source of chance sits outside the pure layers, and the tests
substitute something that always picks the same one (`tests/fakes/chance.py`).
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.domain.ids import ExerciseId

__all__ = ["RandomChooser"]


class RandomChooser:
    """Satisfies `practice.domain.ports.Chooser`."""

    __slots__ = ()

    def choose(self, options: Sequence[ExerciseId]) -> ExerciseId:
        # Which practice problem comes up is not a secret anyone is guarding,
        # so the standard generator is the right one and a CSPRNG would be
        # ceremony.
        return random.choice(options)  # noqa: S311
