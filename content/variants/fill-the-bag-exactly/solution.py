"""Reference solution. CI asserts this passes every test in `tests.py`."""

import math


def best_value(items: list[tuple[int, int]], capacity: int) -> int:
    """Return the most value in a bag filled to exactly `capacity`.

    The 0/1 knapsack loops, untouched: items outside, weights descending
    inside so that no item is counted twice. What differs is the meaning of
    the table and so its first row.

    `best[w]` is the most value at total weight **exactly** `w`. With no
    items the only weight that can be hit is 0, so `best[0]` is 0 and every
    other entry is minus infinity -- "cannot be done". That value propagates
    correctly without being tested for: adding an item's value to it leaves
    it at minus infinity, and `max` never prefers it to a real number.

    Starting everything at 0 instead says an empty bag fills any capacity,
    which is the at-most version of the problem.
    """
    best = [0.0] + [-math.inf] * capacity
    for weight, value in items:
        for total in range(capacity, weight - 1, -1):
            best[total] = max(best[total], best[total - weight] + value)
    return -1 if best[capacity] == -math.inf else int(best[capacity])
