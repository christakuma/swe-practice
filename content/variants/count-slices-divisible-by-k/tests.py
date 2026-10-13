"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import count_subarrays


def by_every_slice(numbers: list[int], k: int) -> int:
    return sum(
        sum(numbers[start:end]) % k == 0
        for start in range(len(numbers))
        for end in range(start + 1, len(numbers) + 1)
    )


def test_counts_the_worked_example() -> None:
    """Counts seven slices divisible by 5 in the worked example."""
    assert count_subarrays([4, 5, 0, -2, -3, 1], 5) == 7


def test_counts_divisible_not_equal() -> None:
    """Counts a slice whose sum is a multiple of k, not only k itself."""
    assert count_subarrays([1, 2, 3], 3) == 3
    assert count_subarrays([6], 3) == 1


def test_counts_zero_and_negative_sums() -> None:
    """Counts sums of zero and negative multiples."""
    assert count_subarrays([0], 7) == 1
    assert count_subarrays([-3, -3], 3) == 3
    assert count_subarrays([2, -2], 5) == 1


def test_counts_a_slice_starting_at_the_first_element() -> None:
    """Counts a slice that begins at index zero."""
    assert count_subarrays([2, 2], 4) == 1
    assert count_subarrays([5], 5) == 1


def test_everything_is_divisible_by_one() -> None:
    """Counts every slice when k is 1."""
    assert count_subarrays([3, 1, 4], 1) == 6
    assert count_subarrays([], 1) == 0


def test_agrees_with_checking_every_slice() -> None:
    """Matches an every-slice check for every short list and small k."""
    for length in range(7):
        for chosen in product(range(-2, 3), repeat=length):
            numbers = list(chosen)
            for k in range(1, 5):
                assert count_subarrays(numbers, k) == by_every_slice(numbers, k), (
                    numbers,
                    k,
                )


def test_counts_in_a_long_list() -> None:
    """Counts slices in a hundred thousand values within the time limit."""
    size = 100_000

    assert count_subarrays([1] * size, size) == 1
    assert count_subarrays([2] * size, 2) == size * (size + 1) // 2
