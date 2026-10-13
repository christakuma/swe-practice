"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import has_duplicate


def by_pairs(numbers: list[int], k: int) -> bool:
    """Compare every pair of positions."""
    return any(
        numbers[first] == numbers[second] and second - first <= k
        for first in range(len(numbers))
        for second in range(first + 1, len(numbers))
    )


def test_finds_a_repeat_within_reach() -> None:
    """Reports True when the repeat is exactly k apart."""
    assert has_duplicate([1, 2, 3, 1], 3) is True


def test_ignores_a_repeat_out_of_reach() -> None:
    """Reports False when the only repeat is further than k apart."""
    assert has_duplicate([1, 2, 3, 1], 2) is False


def test_uses_the_most_recent_copy() -> None:
    """Measures from the nearest earlier copy, not the first one."""
    assert has_duplicate([1, 0, 1, 1], 1) is True
    assert has_duplicate([5, 9, 9, 9, 5, 7, 7], 1) is True


def test_nothing_qualifies_when_k_is_zero() -> None:
    """Reports False for k = 0, even when values repeat."""
    assert has_duplicate([4, 4, 4], 0) is False


def test_handles_short_lists() -> None:
    """Reports False for an empty list and a single value."""
    assert has_duplicate([], 5) is False
    assert has_duplicate([7], 5) is False


def test_agrees_with_comparing_every_pair() -> None:
    """Matches an every-pair check for every short list and every k."""
    for length in range(7):
        for chosen in product(range(3), repeat=length):
            numbers = list(chosen)
            for k in range(7):
                assert has_duplicate(numbers, k) is by_pairs(numbers, k), (numbers, k)


def test_leaves_the_list_alone() -> None:
    """Does not sort or modify the list it was given."""
    numbers = [3, 1, 3]

    has_duplicate(numbers, 2)

    assert numbers == [3, 1, 3]


def test_scans_a_long_list_with_a_long_reach() -> None:
    """Handles 300,000 values and a reach of 100,000 within the time limit.

    Every value is distinct until one repeat at the very end, just inside the
    reach -- and then just outside it. Comparing each value with the k before
    it is thirty billion comparisons.
    """
    size, reach = 300_000, 100_000
    numbers = list(range(size))
    numbers[-1] = numbers[-1 - reach]

    assert has_duplicate(numbers, reach) is True
    assert has_duplicate(numbers, reach - 1) is False
