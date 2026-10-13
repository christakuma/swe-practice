"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations

from bisect import bisect_left, insort
from collections import deque


class WindowMedian:
    """The median of the most recent values of a stream.

    Two views of the same window. `_arrivals` holds it in the order the
    values came, which is the only way to know which one leaves next.
    `_ordered` holds it sorted, which makes the median two index lookups.

    Adding a value inserts it into both. When the window overflows, the
    oldest arrival is popped from the queue and one copy of that value is
    deleted from the sorted list -- found by binary search, so equal values
    elsewhere in the window are untouched.

    Finding the position is logarithmic; shifting the list to open or close
    the gap is linear in the window, though it is a single block move and
    fast in practice. Two heaps with deferred deletion bring that to
    logarithmic at the cost of a good deal more bookkeeping.
    """

    def __init__(self, size: int) -> None:
        """Create an empty stream whose window holds at most `size` values."""
        self._size = size
        self._arrivals: deque[int] = deque()
        self._ordered: list[int] = []

    def add(self, value: int) -> None:
        """Take the next number, pushing out the oldest if the window is full."""
        self._arrivals.append(value)
        insort(self._ordered, value)
        if len(self._arrivals) > self._size:
            leaving = self._arrivals.popleft()
            del self._ordered[bisect_left(self._ordered, leaving)]

    def median(self) -> float:
        """Return the median of the values in the window, as a float."""
        if not self._ordered:
            raise ValueError("no values have been added")
        middle = len(self._ordered) // 2
        if len(self._ordered) % 2:
            return float(self._ordered[middle])
        return (self._ordered[middle - 1] + self._ordered[middle]) / 2
