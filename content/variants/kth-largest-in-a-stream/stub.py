"""Your solution goes here. The tests import from this module."""


class KthLargest:
    """Tracks the kth largest value in a stream of numbers."""

    def __init__(self, k: int) -> None:
        """Create a tracker for the kth largest. `k` is at least 1."""
        raise NotImplementedError

    def add(self, value: int) -> int | None:
        """Take the next number and return the kth largest so far.

        Returns None while fewer than `k` numbers have been added.
        """
        raise NotImplementedError
