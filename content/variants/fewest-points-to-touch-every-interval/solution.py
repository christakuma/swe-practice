"""Reference solution. CI asserts this passes every test in `tests.py`."""


def fewest_points(intervals: list[tuple[int, int]]) -> int:
    """Return the fewest points such that every interval contains one.

    Sorted by end, the first interval must be touched, and its right-hand end
    is the choice that is inside as many later intervals as any other could
    be. Every interval starting at or before that point is already served --
    `>` and not `>=`, because the intervals are closed and a point on the
    boundary counts.
    """
    points = 0
    last: int | None = None
    for start, end in sorted(intervals, key=lambda interval: interval[1]):
        if last is None or start > last:
            points += 1
            last = end
    return points
