"""Your solution goes here. The tests import `best_value` from this module."""


def best_value(items: list[tuple[int, int]], capacity: int) -> int:
    """Return the most value in a bag filled to exactly `capacity`.

    Args:
        items: `(weight, value)` pairs, each usable at most once.
        capacity: the total weight the chosen items must add up to. Never
            negative.

    Returns:
        The greatest total value of a selection whose weights sum to exactly
        `capacity`, or -1 if there is no such selection.
    """
    raise NotImplementedError
