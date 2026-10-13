"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import count_pairs


def by_trying_every_pair(numbers: list[int], target: int) -> int:
    return sum(a + b == target for a, b in combinations(numbers, 2))


def test_counts_pairs_of_different_values() -> None:
    """Counts each pair of positions that reaches the target."""
    assert count_pairs([1, 5, 7, -1], 6) == 2
    assert count_pairs([2, 7, 11, 15], 9) == 1


def test_returns_zero_when_there_are_none() -> None:
    """Returns 0 when no two values add up to the target."""
    assert count_pairs([1, 2, 3], 100) == 0
    assert count_pairs([], 0) == 0
    assert count_pairs([5], 10) == 0


def test_does_not_pair_a_position_with_itself() -> None:
    """Does not count a single value that is half the target."""
    assert count_pairs([3, 4], 6) == 0
    assert count_pairs([0], 0) == 0
    assert count_pairs([5, 1, 2], 10) == 0


def test_equal_values_at_different_positions_are_different_pairs() -> None:
    """Counts by position, so repeated values multiply the pairs."""
    assert count_pairs([1, 1, 1], 2) == 3
    assert count_pairs([1, 1, 1, 1], 2) == 6
    assert count_pairs([3, 3], 6) == 1


def test_a_value_pairs_with_every_copy_of_its_complement() -> None:
    """Counts one pair for each copy of the other value, not one overall."""
    assert count_pairs([2, 4, 2, 4], 6) == 4
    assert count_pairs([1, 9, 9, 9], 10) == 3
    assert count_pairs([9, 9, 9, 1], 10) == 3


def test_a_pair_is_counted_once_not_once_each_way() -> None:
    """Counts positions (i, j) and (j, i) as the same pair."""
    assert count_pairs([1, 2], 3) == 1
    assert count_pairs([4, 6, 5, 5], 10) == 2


def test_handles_negatives_and_zero() -> None:
    """Handles negative values, zeros and a target of zero."""
    assert count_pairs([-3, 3, 0, 0], 0) == 2
    assert count_pairs([-5, -5, -5], -10) == 3
    assert count_pairs([-1, 1, -1, 1], 0) == 4


def test_agrees_with_trying_every_pair() -> None:
    """Matches an exhaustive count for every short list and target.

    Every list of up to six values drawn from -1, 0, 1, 2, 3, against every
    target from -2 to 6.
    """
    for size in range(7):
        for chosen in product((-1, 0, 1, 2, 3), repeat=size):
            numbers = list(chosen)
            for target in range(-2, 7):
                expected = by_trying_every_pair(numbers, target)
                assert count_pairs(numbers, target) == expected, (numbers, target)


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    numbers = [3, 1, 2]

    count_pairs(numbers, 3)

    assert numbers == [3, 1, 2]


def test_counts_thousands_of_millions_of_pairs() -> None:
    """Counts the pairs among a hundred thousand values within the time limit.

    A hundred thousand copies of 7 with a target of 14: every pair of
    positions qualifies, which is n(n - 1) / 2. Then half 3s and half 11s.
    Checking each pair separately is five thousand million additions.
    """
    size = 100_000

    assert count_pairs([7] * size, 14) == size * (size - 1) // 2
    assert count_pairs([3, 11] * (size // 2), 14) == (size // 2) ** 2
    assert count_pairs(list(range(size)), size - 1) == size // 2
