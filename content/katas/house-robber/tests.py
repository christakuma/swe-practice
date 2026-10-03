"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import best_haul


def test_skips_the_middle_of_three() -> None:
    """Takes the two ends rather than the larger middle."""
    assert best_haul([1, 2, 3]) == 4


def test_does_not_simply_alternate() -> None:
    """Chooses values two apart when alternating would be worse.

    Neither alternating pattern is optimal here: positions 0 and 2 give 6, and
    positions 1 and 3 give 6, while taking the two ends -- a gap of two, not
    one -- gives 10.
    """
    assert best_haul([5, 1, 1, 5]) == 10


def test_takes_the_single_largest_when_everything_else_is_adjacent() -> None:
    """Takes one value when the alternatives are all next to it."""
    assert best_haul([2, 100, 2]) == 100


def test_handles_a_single_value() -> None:
    """Takes the only value."""
    assert best_haul([5]) == 5


def test_handles_two_values() -> None:
    """Takes the larger of two adjacent values."""
    assert best_haul([5, 9]) == 9


def test_handles_an_empty_list() -> None:
    """Returns zero when there is nothing to take."""
    assert best_haul([]) == 0


def test_handles_zeroes() -> None:
    """Handles values of zero without being confused by them."""
    assert best_haul([0, 0, 0]) == 0


def test_handles_all_equal_values() -> None:
    """Takes every other value when they are all the same."""
    assert best_haul([4, 4, 4, 4, 4]) == 12


def test_handles_a_longer_run() -> None:
    """Picks the best adjacent-free set out of a longer row."""
    assert best_haul([2, 7, 9, 3, 1]) == 12


def test_handles_a_long_list_quickly() -> None:
    """Solves a list far too long for an exponential search.

    Fifty thousand values. Trying every subset is 2^50000; the recurrence is
    fifty thousand comparisons. Alternating values make the expected answer
    easy to state: take all the nines.
    """
    values = [9, 1] * 25_000

    assert best_haul(values) == 9 * 25_000
