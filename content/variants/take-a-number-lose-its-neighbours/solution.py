"""Reference solution. CI asserts this passes every test in `tests.py`."""


def best_haul(numbers: list[int]) -> int:
    """Return the largest total gained by taking values and losing neighbours.

    Each distinct value is worth itself times its count, and choosing it
    forbids the values one either side. Over the distinct values in sorted
    order that is the row-of-houses recurrence, except that two consecutive
    entries are only "adjacent" when they differ by one.

    A dict rather than an array indexed by value, because the values run to
    a billion and there may be only a handful of them.
    """
    worth: dict[int, int] = {}
    for value in numbers:
        worth[value] = worth.get(value, 0) + value

    taken = skipped = 0
    previous: int | None = None
    for value in sorted(worth):
        best_before = max(taken, skipped)
        if previous is not None and value == previous + 1:
            taken, skipped = skipped + worth[value], best_before
        else:
            taken, skipped = best_before + worth[value], best_before
        previous = value
    return max(taken, skipped)
