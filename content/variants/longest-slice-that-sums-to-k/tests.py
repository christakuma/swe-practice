"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_slice


def by_trying_every_slice(numbers: list[int], target: int) -> int:
    best = 0
    for start in range(len(numbers)):
        total = 0
        for end in range(start, len(numbers)):
            total += numbers[end]
            if total == target:
                best = max(best, end - start + 1)
    return best


def test_finds_the_longer_of_two_slices() -> None:
    """Returns the longest slice when a shorter one also reaches the target."""
    assert longest_slice([1, -1, 5, -2, 3], 3) == 4
    assert longest_slice([-2, -1, 2, 1], 1) == 2


def test_returns_zero_when_no_slice_reaches_the_target() -> None:
    """Returns 0 when nothing adds up to the target."""
    assert longest_slice([1, 2, 3], 7) == 0
    assert longest_slice([], 0) == 0
    assert longest_slice([], 5) == 0


def test_a_slice_may_start_at_the_beginning() -> None:
    """Finds a slice that includes the first element."""
    assert longest_slice([1, 2, 3], 6) == 3
    assert longest_slice([4, 9], 4) == 1


def test_a_slice_may_be_a_single_element() -> None:
    """Finds a slice of one element anywhere in the list."""
    assert longest_slice([5, 1, 9], 9) == 1
    assert longest_slice([5, 1, 9], 1) == 1


def test_zeros_make_a_slice_longer() -> None:
    """Extends a slice across zeros, which do not change its sum."""
    assert longest_slice([0, 0, 0], 0) == 3
    assert longest_slice([0, 3, 0, 0], 3) == 4
    assert longest_slice([2, 0, 0, 5], 2) == 3


def test_negatives_let_a_long_slice_come_back_to_the_target() -> None:
    """Keeps going past a sum that overshoots, because later values may undo it.

    The sum passes 3 and comes back to it; a window that shrinks whenever the
    sum is too large gives up on the long slice.
    """
    assert longest_slice([3, 4, -4, 5, -5], 3) == 5
    assert longest_slice([1, 10, -10, 1], 2) == 4


def test_uses_the_earliest_place_a_prefix_sum_appeared() -> None:
    """Measures from the first time a prefix sum was seen, not the latest.

    The prefix sums are 1, 0, 1, 0, 1: remembering only the latest sighting
    of each makes every slice two long.
    """
    assert longest_slice([1, -1, 1, -1, 1], 0) == 4
    assert longest_slice([2, -2, 2, -2, 5], 5) == 5


def test_handles_a_negative_target() -> None:
    """Finds slices that add up to a negative number."""
    assert longest_slice([1, -3, 2, -4], -5) == 3
    assert longest_slice([-1, -1, -1], -2) == 2


def test_agrees_with_trying_every_slice() -> None:
    """Matches an exhaustive search for every short list and target.

    Every list of up to six values drawn from -2, -1, 0, 1, 3, against every
    target from -4 to 6.
    """
    for size in range(7):
        for chosen in product((-2, -1, 0, 1, 3), repeat=size):
            numbers = list(chosen)
            for target in range(-4, 7):
                expected = by_trying_every_slice(numbers, target)
                assert longest_slice(numbers, target) == expected, (numbers, target)


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    numbers = [1, -1, 2]

    longest_slice(numbers, 2)

    assert numbers == [1, -1, 2]


def test_handles_a_hundred_thousand_values() -> None:
    """Scans a hundred thousand values in one pass, within the time limit.

    Alternating 1 and -1, so every even-length slice sums to 0 and every
    slice starting on a 1 with odd length sums to 1. Trying every slice is
    five thousand million additions.
    """
    numbers = [1, -1] * 50_000

    assert longest_slice(numbers, 0) == 100_000
    assert longest_slice(numbers, 1) == 99_999
    assert longest_slice(numbers, 2) == 0
