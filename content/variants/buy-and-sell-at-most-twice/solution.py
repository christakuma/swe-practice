"""Reference solution. CI asserts this passes every test in `tests.py`."""

import math


def max_profit(prices: list[int]) -> int:
    """Return the largest total profit from at most two trades.

    Four running values, each the most money you could have in your pocket at
    one stage of the plan: holding the first share, having sold it, holding
    the second, having sold that. Every stage is reached from the one before
    it at today's price, or kept as it was.

    `second_buy` is computed from `first_sell`, which is how the second trade
    is funded by the first and why the two cannot overlap. Using today's
    freshly updated values is harmless for the reason the one-trade version
    gives: buying and selling on one day is worth exactly nothing.

    Doing nothing, or stopping after one trade, needs no code. `first_sell`
    starts at 0, and a second trade made on a single day adds 0 to it.
    """
    first_buy = second_buy = -math.inf
    first_sell = second_sell = 0.0
    for price in prices:
        first_buy = max(first_buy, -price)
        first_sell = max(first_sell, first_buy + price)
        second_buy = max(second_buy, first_sell - price)
        second_sell = max(second_sell, second_buy + price)
    return int(second_sell)
