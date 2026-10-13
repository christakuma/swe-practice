"""Your solution goes here. The tests import from this module."""


def best_value(items: list[tuple[int, int]], capacity: int) -> int:
    """Return the most value that fits, with every item reusable.

    Args:
        items: `(weight, value)` pairs, both positive. Each may be taken any
            number of times.
        capacity: the total weight allowed. Zero or more.

    Returns:
        The largest total value of any multiset of items whose total weight
        is within the capacity.
    """
    raise NotImplementedError
