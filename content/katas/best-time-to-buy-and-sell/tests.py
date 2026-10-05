"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import max_profit


def reference(prices: list[int]) -> int:
    """Best profit by comparing every ordered pair -- an independent oracle."""
    return max(
        [0]
        + [
            prices[sell] - prices[buy]
            for buy in range(len(prices))
            for sell in range(buy + 1, len(prices))
        ]
    )


def test_finds_the_best_pair() -> None:
    """Returns the largest profit available."""
    assert max_profit([7, 1, 5, 3, 6, 4]) == 5


def test_returns_zero_when_prices_only_fall() -> None:
    """Returns 0 when no later day is higher than an earlier one."""
    assert max_profit([7, 6, 4, 3, 1]) == 0


def test_handles_an_empty_list() -> None:
    """Returns 0 for no prices at all."""
    assert max_profit([]) == 0


def test_handles_a_single_day() -> None:
    """Returns 0 for one day, which has no later day to sell on."""
    assert max_profit([5]) == 0


def test_refuses_to_sell_before_buying() -> None:
    """Returns 0 when the maximum comes before the minimum.

    The largest and smallest values are both present and in the wrong order.
    A solution that returns `max(prices) - min(prices)` reports 9 here.
    """
    assert max_profit([10, 1]) == 0


def test_does_not_pair_the_global_extremes_when_order_forbids_it() -> None:
    """Picks the best ordered pair, not the best unordered one.

    max is 9 and min is 1, which would give 8; but the 9 precedes the 1, so
    the real answer is the 5-to-7 pair.
    """
    assert max_profit([5, 9, 1, 7]) == 6


def test_handles_a_rising_series() -> None:
    """Buys first and sells last when prices only rise."""
    assert max_profit([1, 2, 3, 4, 5]) == 4


def test_handles_all_prices_equal() -> None:
    """Returns 0 when every day costs the same."""
    assert max_profit([3, 3, 3, 3]) == 0


def test_handles_two_days() -> None:
    """Handles both arrangements of a two-day list."""
    assert max_profit([1, 5]) == 4
    assert max_profit([5, 1]) == 0


def test_finds_a_profit_that_spans_a_dip() -> None:
    """Keeps the best buy price across a later, shallower trough.

    The cheapest day is day 1, and the best sell is day 5 -- but a solution
    that resets its buy price at every local minimum takes the 2-to-8 pair
    instead of 1-to-9.
    """
    assert max_profit([3, 1, 4, 2, 8, 9]) == 8


def test_handles_negative_prices() -> None:
    """Works for values below zero, which the arithmetic does not care about."""
    assert max_profit([-5, -3, -8, -1]) == 7
    assert max_profit([-1, -2, -3]) == 0


def test_agrees_with_a_brute_force_on_every_short_series() -> None:
    """Matches an all-pairs search for every list up to length seven.

    Every price list over five distinct values, which is about a hundred
    thousand cases. The ordering constraint is the thing solutions get wrong,
    and it only bites on particular arrangements of the max and the min.
    """
    for length in range(8):
        for prices in product(range(5), repeat=length):
            values = list(prices)

            assert max_profit(values) == reference(values), values


def test_leaves_the_input_alone() -> None:
    """Does not sort or mutate the list it was given."""
    prices = [7, 1, 5, 3, 6, 4]
    original = list(prices)

    max_profit(prices)

    assert prices == original


def test_scans_a_large_series_in_one_pass() -> None:
    """Handles a million days within the time limit.

    Comparing every pair is five times ten to the eleventh here. The series
    falls for half a million days and then rises, so the cheapest day is the
    trough in the middle and the best sell is the very last day -- which also
    rules out a solution that only considers a bounded window.
    """
    half = 500_000
    prices = [1_000_000 - value for value in range(half)]
    prices += list(range(half))

    assert max_profit(prices) == half - 1
