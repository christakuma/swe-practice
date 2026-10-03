"""Your solution goes here. The tests import `best_value` from here."""


def best_value(items: list[tuple[int, int]], capacity: int) -> int:
    """Return the most value that fits in the capacity.

    Each item may be taken at most once, and cannot be split.

    Args:
        items: `(weight, value)` pairs, both positive.
        capacity: the total weight allowed. Zero or more.

    Returns:
        The largest total value of any subset whose total weight is within the
        capacity.
    """
    raise NotImplementedError
