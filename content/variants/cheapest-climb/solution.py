"""Reference solution. CI asserts this passes every test in `tests.py`."""


def cheapest_climb(costs: list[int]) -> int:
    """Return the lowest total cost of climbing past the last step.

    The counting recurrence with `min` where the sum was. The cheapest way to
    stand on a step is its own cost plus the cheaper of the two places below
    it, and only those two values are ever read, so two variables carry the
    whole table.

    Both start at 0, and those zeros are the floor: the first step is reached
    from the floor, and so is the second. At the end the two variables hold
    the cheapest way to stand on each of the last two steps, and the landing
    is one free move from either.
    """
    before, last = 0, 0
    for cost in costs:
        before, last = last, cost + min(before, last)
    return min(before, last)
