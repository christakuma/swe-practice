"""Reference solution. CI asserts this passes every test in `tests.py`."""

import heapq


class MedianStream:
    """A running median over a stream of numbers.

    **You never need the whole collection ordered -- only the middle of it.**
    That is the observation the whole structure follows from: a sorted list
    maintains an ordering over every element to answer a question about one or
    two of them, and pays O(n) per insertion for the privilege.

    So keep the numbers in two halves and arrange for the middle to be the part
    you can reach. A max-heap over the low half and a min-heap over the high
    half put the two candidate middle values at the two heap tops, which makes
    `median` O(1) and `add` O(log n).

    Two invariants, restored after every insertion:

    1. every value in `_low` is at most every value in `_high`;
    2. `len(_low) - len(_high)` is 0 or 1 -- the low half holds the extra
       element on an odd count.

    The insertion enforces (1) **without comparing anything**, which is the
    trick worth remembering: push onto `_low`, then immediately move `_low`'s
    top across to `_high`. Whatever the new value was, the largest of the low
    half ends up on the high side, so the ordering cannot be violated. Then
    rebalance for (2). Writing it as "compare with the top and choose a heap"
    also works and needs a case for the empty heap; this version has no
    branches at all on the way in.

    `heapq` is a min-heap only, so `_low` stores **negated** values and its
    "top" is `-_low[0]`. That negation is the one place sign errors live, and
    it is why the two halves are never iterated or printed together.

    With (2) in place, `median` needs no size arithmetic beyond a parity check:
    the halves are equal on an even count (average the two tops) and `_low` is
    one longer on an odd count (its top is the median).
    """

    def __init__(self) -> None:
        """Create an empty stream."""
        self._low: list[int] = []  # max-heap, negated: the smaller half
        self._high: list[int] = []  # min-heap: the larger half

    def add(self, value: int) -> None:
        """Take the next number."""
        heapq.heappush(self._low, -value)
        # Hand the low half's largest to the high half: the ordering invariant
        # is restored by construction rather than by comparison.
        heapq.heappush(self._high, -heapq.heappop(self._low))
        if len(self._high) > len(self._low):
            heapq.heappush(self._low, -heapq.heappop(self._high))

    def median(self) -> float:
        """Return the median of everything added so far.

        Raises:
            ValueError: if nothing has been added.
        """
        if not self._low:
            raise ValueError("no values have been added")
        if len(self._low) > len(self._high):
            return float(-self._low[0])
        return (-self._low[0] + self._high[0]) / 2
