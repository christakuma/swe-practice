"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations

from solution import ways_to_make


def by_choosing(coins: tuple[int, ...], amount: int) -> int:
    """Decide how many of the first coin to use, then recurse on the rest."""
    if not coins:
        return 1 if amount == 0 else 0
    first, rest = coins[0], coins[1:]
    return sum(by_choosing(rest, amount - used) for used in range(0, amount + 1, first))


def test_counts_the_combinations() -> None:
    """Counts four ways to make 5 from coins of 1, 2 and 5."""
    assert ways_to_make([1, 2, 5], 5) == 4


def test_counts_a_combination_once_whatever_its_order() -> None:
    """Counts 1+2 and 2+1 as one combination."""
    assert ways_to_make([1, 2], 3) == 2
    assert ways_to_make([1, 2, 3], 4) == 4


def test_returns_zero_when_the_amount_cannot_be_made() -> None:
    """Returns 0 when no combination reaches the amount."""
    assert ways_to_make([2], 3) == 0
    assert ways_to_make([5, 10], 3) == 0


def test_counts_one_way_to_make_nothing() -> None:
    """Counts one way to make zero, with or without coins."""
    assert ways_to_make([1, 2, 5], 0) == 1
    assert ways_to_make([], 0) == 1


def test_returns_zero_for_a_positive_amount_and_no_coins() -> None:
    """Returns 0 when there are no coins and something to make."""
    assert ways_to_make([], 7) == 0


def test_does_not_depend_on_the_order_of_the_coins() -> None:
    """Gives the same count however the coins are listed."""
    assert ways_to_make([5, 1, 2], 11) == ways_to_make([1, 2, 5], 11) == 11


def test_agrees_with_choosing_a_count_for_each_coin() -> None:
    """Matches a count-per-coin enumeration for every small case.

    Every set of one to three coins drawn from 1..6, at every amount up to
    fourteen.
    """
    for size in range(1, 4):
        for coins in combinations(range(1, 7), size):
            for amount in range(15):
                expected = by_choosing(coins, amount)
                assert ways_to_make(list(coins), amount) == expected, (coins, amount)


def test_counts_the_ways_to_make_two_pounds() -> None:
    """Counts 73,682 ways to make 200 from eight British coins."""
    assert ways_to_make([1, 2, 5, 10, 20, 50, 100, 200], 200) == 73_682


def test_leaves_the_coins_alone() -> None:
    """Does not sort or modify the list of coins."""
    coins = [5, 1, 2]

    ways_to_make(coins, 6)

    assert coins == [5, 1, 2]


def test_counts_a_large_amount_within_the_time_limit() -> None:
    """Counts the ways to make ten thousand from 1, 2 and 5.

    Checked against a closed form: fix the number of fives, and what is left
    can be made from ones and twos in (remainder // 2) + 1 ways.
    """
    amount = 10_000
    expected = sum((amount - fives) // 2 + 1 for fives in range(0, amount + 1, 5))

    assert ways_to_make([1, 2, 5], amount) == expected
