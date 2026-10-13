"""Reference solution. CI asserts this passes every test in `tests.py`."""

from bisect import bisect_right


def most_valuable(intervals: list[tuple[int, int, int]]) -> int:
    """Return the largest total value of a set of non-overlapping intervals.

    Sorted by end, the intervals compatible with any one of them -- those
    that finish at or before it starts -- are a prefix of the list. That
    turns the choice into a recurrence: `best[i]`, the most the first `i`
    intervals can be worth, is the better of leaving interval `i` out
    (`best[i - 1]`) and taking it (`value + best[prefix]`).

    `bisect_right` over the ends finds the prefix: it counts the intervals
    ending at or before `start`, and "or at" is what lets touching intervals
    sit side by side. The search is limited to the intervals before this one,
    which matters only for the reader -- an interval's own end is always
    after its start.
    """
    ordered = sorted(intervals, key=lambda interval: interval[1])
    ends = [end for _, end, _ in ordered]
    best = [0]
    for index, (start, _, value) in enumerate(ordered):
        compatible = bisect_right(ends, start, 0, index)
        best.append(max(best[-1], value + best[compatible]))
    return best[-1]
