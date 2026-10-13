"""Reference solution. CI asserts this passes every test in `tests.py`."""


def merge_intervals(
    intervals: list[tuple[int, int]], gap: int
) -> list[tuple[int, int]]:
    """Merge intervals that overlap or lie within `gap` of each other.

    The standard sweep with a tolerance in its one comparison. After sorting
    by start, an interval joins the one being built if it starts no more
    than `gap` beyond that one's end.

    Chains fall out of comparing against the *built* interval and not the
    original ones: when B joins A the end moves out to B's, and C is then
    measured from there.

    The tolerance belongs in the comparison and nowhere else. Padding the
    intervals themselves and merging as usual produces padded output, and
    padding both ends of each makes two intervals reach towards each other,
    which merges them at twice the gap.
    """
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if merged and start - merged[-1][1] <= gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
