"""Reference solution. CI asserts this passes every test in `tests.py`."""


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge the half-open intervals that overlap.

    Sorted by start, each interval either begins strictly inside the group
    being built -- in which case it joins, and may extend the group's end --
    or it does not, and starts a new group. `<` rather than `<=` is the whole
    difference from the closed version: an interval that begins exactly where
    the group ends shares no time with it.

    `max` on the end, because an interval can lie wholly inside the group and
    must not pull its end backwards.
    """
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
