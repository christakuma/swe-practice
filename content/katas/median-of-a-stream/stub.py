"""Your solution goes here.

The tests import `MedianStream` from this module.
"""


class MedianStream:
    """A running median over a stream of numbers."""

    def __init__(self) -> None:
        """Create an empty stream."""
        raise NotImplementedError

    def add(self, value: int) -> None:
        """Take the next number."""
        raise NotImplementedError

    def median(self) -> float:
        """Return the median of everything added so far.

        Raises:
            ValueError: if nothing has been added.
        """
        raise NotImplementedError
