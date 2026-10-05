"""Reference solution. CI asserts this passes every test in `tests.py`."""


def insert(
    intervals: list[tuple[int, int]],
    new: tuple[int, int],
) -> list[tuple[int, int]]:
    """Insert `new` into a sorted, non-overlapping list, merging overlaps.

    The input is already sorted and already disjoint, which means the intervals
    fall into **three consecutive groups**: those entirely before `new`, those
    that touch it, and those entirely after. One pass handles each in turn, and
    recognising that the groups are contiguous is what makes this O(n) with no
    sorting -- `merge-intervals` has to sort because its input is unordered;
    this one must not, because that would throw away the guarantee it was given.

    The absorbing step widens `new` rather than emitting anything: take the
    smaller start and the larger end for each overlapping interval, and emit
    once the run is over. Emitting as you go cannot work, because a later
    interval may extend the same merged block -- which is the whole of the
    second worked example, where `(4, 8)` swallows three separate intervals.

    **`end < start` and not `end <= start`.** Touching counts as overlapping,
    so `(1, 3)` and `(3, 5)` merge. One character decides it, and it decides it
    twice -- once for each of the two boundary comparisons -- so a solution that
    gets one right and the other wrong merges on the left and not on the right.

    The three loops share an index deliberately rather than slicing, so there is
    exactly one place the position advances and the groups cannot overlap or
    skip.
    """
    result: list[tuple[int, int]] = []
    start, end = new
    index = 0
    count = len(intervals)

    while index < count and intervals[index][1] < start:
        result.append(intervals[index])
        index += 1

    while index < count and intervals[index][0] <= end:
        start = min(start, intervals[index][0])
        end = max(end, intervals[index][1])
        index += 1
    result.append((start, end))

    result.extend(intervals[index:])
    return result
