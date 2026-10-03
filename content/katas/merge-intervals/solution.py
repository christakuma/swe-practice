"""Reference solution. CI asserts this passes every test in `tests.py`."""


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping intervals into the fewest intervals that cover them.

    Sorting by start is the whole algorithm. Unsorted, "does this interval
    overlap anything I have already seen" is a question about the entire set, and
    answering it per interval is quadratic. Sorted, it is a question about the
    *last* interval only -- because anything earlier ends no later than that one
    does, so if the new interval misses the last one it misses all of them.

    `current_start <= last_end` rather than `<` is the decision this problem
    turns on, and it is a judgement about the domain rather than about code:
    (1, 3) and (3, 5) are treated as touching and merged, because for a closed
    interval 3 belongs to both. Change the comparison and (1, 3), (3, 5) comes
    back as two intervals -- which is the right answer for a half-open interval.
    Either is defensible; shipping without deciding is not.
    """
    if not intervals:
        return []

    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            last_start, last_end = merged[-1]
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged
