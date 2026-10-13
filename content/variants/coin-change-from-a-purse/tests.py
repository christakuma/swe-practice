"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, combinations_with_replacement

from solution import fewest_coins


def by_search(coins: list[int], amount: int) -> int:
    """The smallest selection of positions that sums to the amount."""
    for size in range(len(coins) + 1):
        for chosen in combinations(coins, size):
            if sum(chosen) == amount:
                return size
    return -1


def test_makes_an_amount_from_distinct_coins() -> None:
    """Finds the fewest coins when a selection exists."""
    assert fewest_coins([1, 5, 10], 11) == 2
    assert fewest_coins([1, 2, 5, 10], 18) == 4


def test_does_not_spend_a_coin_twice() -> None:
    """Returns -1 when the amount needs one coin more than once."""
    assert fewest_coins([1, 5, 10], 3) == -1
    assert fewest_coins([5], 10) == -1
    assert fewest_coins([2, 3], 4) == -1


def test_equal_values_are_separate_coins() -> None:
    """Spends two coins of the same value when the purse holds two."""
    assert fewest_coins([2, 2, 3], 4) == 2
    assert fewest_coins([5, 5, 5], 15) == 3
    assert fewest_coins([5, 5, 5], 20) == -1


def test_prefers_fewer_coins() -> None:
    """Chooses the smaller of two selections that both work."""
    assert fewest_coins([1, 1, 1, 3], 3) == 1
    assert fewest_coins([1, 2, 3, 4, 5], 9) == 2


def test_is_not_greedy() -> None:
    """Passes over the largest coin when taking it leaves no way to finish."""
    assert fewest_coins([4, 3, 3], 6) == 2
    assert fewest_coins([7, 5, 5, 1], 10) == 2


def test_an_amount_of_zero_needs_no_coins() -> None:
    """Returns 0 for an amount of zero, with or without coins."""
    assert fewest_coins([1, 2, 3], 0) == 0
    assert fewest_coins([], 0) == 0


def test_an_empty_purse_makes_nothing_else() -> None:
    """Returns -1 for any positive amount when there are no coins."""
    assert fewest_coins([], 1) == -1
    assert fewest_coins([], 50) == -1


def test_the_whole_purse_is_the_most_it_can_make() -> None:
    """Uses every coin for the total, and fails one beyond it."""
    assert fewest_coins([3, 1, 4, 1, 5], 14) == 5
    assert fewest_coins([3, 1, 4, 1, 5], 15) == -1


def test_the_order_of_the_coins_does_not_matter() -> None:
    """Gives the same answer however the purse is arranged."""
    assert fewest_coins([1, 6, 3, 2], 5) == 2
    assert fewest_coins([6, 3, 2, 1], 5) == 2
    assert fewest_coins([2, 1, 6, 3], 5) == 2


def test_agrees_with_trying_every_selection() -> None:
    """Matches a search of every subset for every small purse.

    Every purse of up to five coins drawn from 1..5, repeats allowed, against
    every amount from 0 to one more than the purse holds.
    """
    for size in range(6):
        for chosen in combinations_with_replacement(range(1, 6), size):
            coins = list(chosen)
            for amount in range(sum(coins) + 2):
                assert fewest_coins(coins, amount) == by_search(coins, amount), (
                    coins,
                    amount,
                )


def test_leaves_the_purse_alone() -> None:
    """Does not modify the list it was given."""
    coins = [5, 1, 2]

    fewest_coins(coins, 3)

    assert coins == [5, 1, 2]


def test_handles_a_full_purse() -> None:
    """Handles a hundred coins and an amount of five thousand.

    The coins are 1 to 100. The ninety largest total 4,995, so ninety coins
    cannot make 5,000 and ninety-one can: those ninety and the 5.
    """
    coins = list(range(1, 101))

    assert sum(coins[-90:]) == 4995
    assert fewest_coins(coins, 5000) == 91
    assert fewest_coins(coins, 199) == 2
    assert fewest_coins(coins, 5049) == 99
