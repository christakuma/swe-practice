"""Reference solution. CI asserts this passes every test in `tests.py`."""


def best_value(items: list[tuple[int, int]], capacity: int) -> int:
    """Return the most value that fits, with every item reusable.

    `best[room]` is the most value for that much capacity. For each item the
    capacities are visited upwards, so `best[room - weight]` has already been
    updated for this item and may contain copies of it. That is what allows
    reuse -- and it is the one difference from the take-at-most-once table,
    which goes downwards to prevent it.
    """
    best = [0] * (capacity + 1)
    for weight, value in items:
        for room in range(weight, capacity + 1):
            best[room] = max(best[room], best[room - weight] + value)
    return best[capacity]
