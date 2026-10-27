"""Your solution goes here.

The tests import `WindowMedian` from this module.
"""

from __future__ import annotations


class WindowMedian:
    """The median of the most recent values of a stream."""

    def __init__(self, size: int) -> None:
        """Create an empty stream whose window holds at most `size` values.

        Args:
            size: how many of the most recent values the window keeps.
        """
        raise NotImplementedError

    def add(self, value: int) -> None:
        """Take the next number, pushing out the oldest if the window is full.

        Args:
            value: the number to add to the stream.
        """
        raise NotImplementedError

    def median(self) -> float:
        """Return the median of the values in the window, as a float.

        Returns:
            The middle value of the window, or the mean of the two middle
            values when the window holds an even number of them.

        Raises:
            ValueError: if nothing has been added yet.
        """
        raise NotImplementedError
