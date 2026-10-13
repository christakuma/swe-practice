"""Reference solution. CI asserts this passes every test in `tests.py`."""

#: The largest circle in which every house is within two places of every
#: other, so only one can be taken.
ALL_WITHIN_REACH = 5


def _row(values: list[int]) -> int:
    """The best total from a straight row with the same wider alarm."""
    three_back = two_back = best = 0
    for value in values:
        three_back, two_back, best = two_back, best, max(best, three_back + value)
    return best


def best_haul(houses: list[int]) -> int:
    """Return the largest total takeable when taken houses are 3 or more apart.

    Up to five houses, every pair is within two places, so the answer is the
    single largest. Beyond that the circle is cut into rows.

    Consider the four houses at the join: the last two and the first two. A
    valid selection takes at most two of them, and if two, they are the
    second-to-last and the second. So every selection avoids the first two
    houses, or avoids the last two, or avoids the last and the first -- and
    within each of those rows, the row's own rule is all that is left to
    enforce.
    """
    if len(houses) <= ALL_WITHIN_REACH:
        return max(houses, default=0)
    return max(_row(houses[2:]), _row(houses[:-2]), _row(houses[1:-1]))
