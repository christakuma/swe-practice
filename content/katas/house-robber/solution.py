"""Reference solution. CI asserts this passes every test in `tests.py`."""


def best_haul(values: list[int]) -> int:
    """Return the largest total obtainable without taking two adjacent values.

    The recurrence is the "what did I decide about the last one" question again.
    Either you take the last house -- then you may not take the one before it, so
    you add it to the best for everything up to two back -- or you skip it, and
    the answer is the best for everything up to one back.

    `best(i) = max(best(i - 1), best(i - 2) + values[i])`

    Greedy does not work here, which is the thing to be convinced of rather than
    told. "Take every other house" fails `[1, 2, 9, 4]`: alternating from the
    start gives 1 + 9 = 10, alternating from the second gives 2 + 4 = 6, and the
    best is 2 + 9... which is not alternating at all -- it is adjacent-free with
    a gap of one, and worth 11. The optimal choice at each house depends on the
    whole prefix, which is what makes it DP and not greed.

    Two variables, because the recurrence looks back two places. `take` and
    `skip` are the same two numbers the table would hold.
    """
    take = 0
    skip = 0
    for value in values:
        take, skip = skip + value, max(skip, take)
    return max(take, skip)
