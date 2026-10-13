"""Your solution goes here."""


def merge_intervals(
    intervals: list[tuple[int, int]], gap: int
) -> list[tuple[int, int]]:
    """Merge intervals that overlap or lie within `gap` of each other.

    Args:
        intervals: `(start, end)` pairs with `start <= end`. In any order, and
            may overlap or touch.
        gap: the largest distance between two intervals that still merges
            them. Never negative.

    Returns:
        The merged intervals, sorted by start. Each runs from the earliest
        start to the latest end of the intervals merged into it.
    """
    raise NotImplementedError
