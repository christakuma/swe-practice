"""Your solution goes here. The tests import `insert` from this module."""


def insert(
    intervals: list[tuple[int, int]],
    new: tuple[int, int],
) -> list[tuple[int, int]]:
    """Insert `new` into a sorted, non-overlapping list, merging overlaps.

    Args:
        intervals: non-overlapping `(start, end)` pairs in ascending order.
            May be empty.
        new: the interval to insert, with `start <= end`.

    Returns:
        The intervals after insertion: still ascending, still non-overlapping,
        with anything `new` touched merged into it.
    """
    raise NotImplementedError
