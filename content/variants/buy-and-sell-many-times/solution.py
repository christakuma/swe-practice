"""Reference solution. CI asserts this passes every test in `tests.py`."""

from itertools import pairwise


def max_profit(prices: list[int]) -> int:
    """Return the largest total profit from any number of trades.

    Every rise from one day to the next is collected and every fall is sat
    out. That is optimal because a trade across several rising days is worth
    exactly the sum of its daily rises, so nothing is lost by taking them one
    day at a time -- and nothing can be gained from a day the price fell.
    """
    return sum(max(later - earlier, 0) for earlier, later in pairwise(prices))
