"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import fewest_coins


def test_makes_an_amount_from_three_coins() -> None:
    """Finds the fewest coins for a reachable amount."""
    assert fewest_coins([1, 2, 5], 11) == 3


def test_beats_the_greedy_choice() -> None:
    """Chooses two medium coins over one large coin and two small ones.

    Greedy takes the 4, then two 1s, for three coins. Two 3s is better, and no
    rule about picking the largest coin first finds it.
    """
    assert fewest_coins([1, 3, 4], 6) == 2


def test_reports_an_unreachable_amount() -> None:
    """Returns -1 when no combination reaches the amount."""
    assert fewest_coins([2], 3) == -1


def test_reports_an_unreachable_amount_with_several_coins() -> None:
    """Returns -1 when the coins cannot combine to the amount."""
    assert fewest_coins([3, 5], 7) == -1


def test_needs_no_coins_for_zero() -> None:
    """Returns zero for an amount of zero."""
    assert fewest_coins([1], 0) == 0


def test_handles_an_amount_equal_to_one_coin() -> None:
    """Returns one when a single coin is exactly the amount."""
    assert fewest_coins([5, 10, 25], 10) == 1


def test_handles_coins_larger_than_the_amount() -> None:
    """Ignores coins too large to use."""
    assert fewest_coins([7, 10], 14) == 2


def test_handles_a_realistic_coin_set() -> None:
    """Makes an awkward amount from a realistic set of coins."""
    assert fewest_coins([1, 5, 10, 25], 63) == 6


def test_handles_no_coins_at_all() -> None:
    """Returns -1 for a positive amount with no coins."""
    assert fewest_coins([], 5) == -1


def test_handles_a_large_amount_quickly() -> None:
    """Solves an amount far too large for an exponential search.

    Five thousand, from three coin values. Enumerating combinations is
    hopeless; the table is five thousand rows of three comparisons.
    """
    assert fewest_coins([1, 2, 5], 5_000) == 1_000
