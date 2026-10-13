"""Your solution goes here.

The tests import `WindowMedian` from this module.
"""

from __future__ import annotations


class WindowMedian:
    """The median of the most recent values of a stream."""

    def __init__(self, size: int) -> None:
        """Create an empty stream whose window holds at most `size` values."""
        raise NotImplementedError

    def add(self, value: int) -> None:
        """Take the next number, pushing out the oldest if the window is full."""
        raise NotImplementedError

    def median(self) -> float:
        """Return the median of the values in the window, as a float.

        Raises:
            ValueError: if nothing has been added yet.
        """
        raise NotImplementedError
