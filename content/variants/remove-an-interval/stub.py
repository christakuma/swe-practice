"""Your solution goes here. The tests import from this module."""


def remove(
    intervals: list[tuple[int, int]],
    gone: tuple[int, int],
) -> list[tuple[int, int]]:
    """Remove `gone` from a sorted list of non-overlapping half-open intervals.

    Args:
        intervals: `(start, end)` pairs with `start < end`, ascending and
            non-overlapping. May be empty. Not to be modified.
        gone: the stretch to remove, with `start < end`.

    Returns:
        What is left: ascending, non-overlapping, and with no empty interval.
    """
    raise NotImplementedError
