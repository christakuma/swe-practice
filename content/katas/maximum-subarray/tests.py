"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import max_slice_sum


def test_finds_a_slice_in_the_middle() -> None:
    """Finds the best slice when it is neither at the start nor the end."""
    assert max_slice_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6


def test_handles_a_list_of_all_positives() -> None:
    """Takes the whole list when every value is positive."""
    assert max_slice_sum([1, 2, 3, 4]) == 10


def test_handles_a_list_of_all_negatives() -> None:
    """Returns the least negative value when every value is negative.

    The case that rules out initialising the running sums to zero. A solution
    that does returns 0 -- which is not the sum of any slice of this list.
    """
    assert max_slice_sum([-3, -1, -2]) == -1


def test_handles_a_single_element() -> None:
    """Returns the only element."""
    assert max_slice_sum([7]) == 7


def test_handles_a_single_negative_element() -> None:
    """Returns the only element even when it is negative."""
    assert max_slice_sum([-7]) == -7


def test_crosses_a_small_dip() -> None:
    """Keeps going through a negative value worth paying for."""
    assert max_slice_sum([5, -1, 5]) == 9


def test_does_not_cross_a_large_dip() -> None:
    """Starts again after a negative value too costly to cross.

    Crossing the -100 would cost more than the 5 before it is worth, so the
    answer is the 6 on its own and not 5 - 100 + 6.
    """
    assert max_slice_sum([5, -100, 6]) == 6


def test_handles_zeroes() -> None:
    """Treats zeros as free to include or skip."""
    assert max_slice_sum([0, -1, 0, 2, 0]) == 2


def test_finds_the_best_of_two_candidate_slices() -> None:
    """Returns the better of two separated positive runs."""
    assert max_slice_sum([3, 3, -10, 4, 4]) == 8


def test_handles_a_long_list_quickly() -> None:
    """Scans a list far too long to try every slice.

    Fifty thousand elements, which is more than a billion slices. Kadane's is
    one pass; the nested-loop version is not going to finish.
    """
    numbers = [1, -2] * 25_000
    numbers[0] = 100

    assert max_slice_sum(numbers) == 100
