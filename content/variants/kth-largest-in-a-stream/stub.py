"""Your solution goes here. The tests import from this module."""


class KthLargest:
    """Tracks the kth largest value in a stream of numbers."""

    def __init__(self, k: int) -> None:
        """Create a tracker for the kth largest.

        Args:
            k: which largest to track. At least 1.
        """
        raise NotImplementedError

    def add(self, value: int) -> int | None:
        """Take the next number and return the kth largest so far.

        Args:
            value: the number to add to the stream.

        Returns:
            The kth largest value added so far, or None while fewer than `k`
            numbers have been added.
        """
        raise NotImplementedError
