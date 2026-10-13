"""Reference solution. CI asserts this passes every test in `tests.py`."""

import heapq


class KthLargest:
    """Tracks the kth largest value in a stream of numbers.

    A min-heap holding the k largest values seen. Its smallest entry is the
    kth largest overall, and a value that would be smaller than every entry
    is pushed and popped straight out again -- it could never matter.
    """

    def __init__(self, k: int) -> None:
        self._k = k
        self._largest: list[int] = []

    def add(self, value: int) -> int | None:
        if len(self._largest) < self._k:
            heapq.heappush(self._largest, value)
        else:
            heapq.heappushpop(self._largest, value)
        return self._largest[0] if len(self._largest) == self._k else None
