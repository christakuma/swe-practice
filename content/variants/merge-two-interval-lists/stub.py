"""Your solution goes here. The tests import `merge_lists` from this module."""


def merge_lists(
    first: list[tuple[int, int]],
    second: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Return the union of two sorted lists of intervals.

    Args:
        first: non-overlapping `(start, end)` pairs in ascending order. May
            be empty.
        second: another such list.

    Returns:
        A new list, ascending and non-overlapping, covering exactly the
        points covered by either input. Intervals that touch are merged.
    """
    raise NotImplementedError
