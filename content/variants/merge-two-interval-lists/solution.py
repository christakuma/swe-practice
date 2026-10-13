"""Reference solution. CI asserts this passes every test in `tests.py`."""


def merge_lists(
    first: list[tuple[int, int]],
    second: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Return the union of two sorted lists of intervals.

    Two steps braided into one loop. Choosing whichever list has the earlier
    next start yields every interval in order of start -- merge sort's merge
    -- and intervals that arrive in that order can be folded into the result
    one at a time: each either overlaps the last interval already there, and
    stretches it, or begins a new one.

    Nothing about which list an interval came from matters after it has been
    chosen. That is why an interval from one list can absorb any number from
    the other without a special case: they simply keep arriving and keep
    overlapping the last result.
    """
    merged: list[tuple[int, int]] = []
    i = j = 0
    while i < len(first) or j < len(second):
        if j == len(second) or (i < len(first) and first[i][0] <= second[j][0]):
            start, end = first[i]
            i += 1
        else:
            start, end = second[j]
            j += 1
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
