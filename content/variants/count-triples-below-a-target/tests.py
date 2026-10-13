"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product
from math import comb

from solution import count_triples


def by_listing(numbers: list[int], target: int) -> int:
    """The count by looking at every triple. An oracle for short lists."""
    return sum(1 for triple in combinations(numbers, 3) if sum(triple) < target)


def test_counts_the_triples_below_the_target() -> None:
    """Counts two of the four triples in a short list."""
    assert count_triples([-2, 0, 1, 3], 2) == 2


def test_fewer_than_three_values_give_zero() -> None:
    """Returns zero when there are not three positions to choose."""
    assert count_triples([], 10) == 0
    assert count_triples([1], 10) == 0
    assert count_triples([1, 2], 100) == 0


def test_a_sum_equal_to_the_target_does_not_count() -> None:
    """Counts only sums strictly below the target."""
    assert count_triples([5, 1, 3], 9) == 0
    assert count_triples([5, 1, 3], 10) == 1
    assert count_triples([0, 0, 0], 0) == 0


def test_equal_values_at_different_positions_count_separately() -> None:
    """Counts every choice of positions, not every distinct triple of values.

    Skipping repeats, as three-sum does to avoid duplicate triples, counts
    one here where there are four.
    """
    assert count_triples([1, 1, 1, 1], 4) == 4
    assert count_triples([2, 2, 2, 2, 2], 7) == 10
    assert count_triples([0, 0, 1, 1], 2) == 2


def test_counts_a_whole_block_of_partners_at_once() -> None:
    """Counts every triple when all of them qualify.

    Six values far below the target: twenty triples, and each one found by
    the pointers stands for several more.
    """
    assert count_triples([1, 2, 3, 4, 5, 6], 100) == 20
    assert count_triples([1, 2, 3, 4, 5, 6], 8) == 2
    assert count_triples([1, 2, 3, 4, 5, 6], 9) == 4
    assert count_triples([1, 2, 3, 4, 5, 6], 10) == 7


def test_handles_negative_values_and_a_negative_target() -> None:
    """Counts correctly when the values and the target are below zero."""
    assert count_triples([-5, -4, -3, -2, -1], -8) == 6
    assert count_triples([-5, -4, -3, -2, -1], -9) == 4
    assert count_triples([-1, 0, 1], 0) == 0
    assert count_triples([-1, 0, 1], 1) == 1


def test_the_order_of_the_list_does_not_matter() -> None:
    """Returns the same count however the values are arranged."""
    assert count_triples([3, -2, 1, 0], 2) == 2
    assert count_triples([6, 1, 5, 2, 4, 3], 10) == 7


def test_leaves_the_list_as_it_was() -> None:
    """Does not sort or otherwise change the list it was given."""
    numbers = [3, -2, 1, 0]

    count_triples(numbers, 2)

    assert numbers == [3, -2, 1, 0]


def test_agrees_with_listing_every_triple() -> None:
    """Matches a count of every triple on every short list and every nearby target.

    Every list of up to five values from -2 to 2, with targets from -4 to 4.
    """
    for size in range(6):
        for values in product(range(-2, 3), repeat=size):
            numbers = list(values)
            for target in range(-4, 5):
                assert count_triples(numbers, target) == by_listing(numbers, target), (
                    numbers,
                    target,
                )


def test_agrees_with_listing_on_longer_lists() -> None:
    """Matches the same count on lists of a dozen values with a wider spread."""
    for seed in range(40):
        numbers = [(seed * 37 + step * step * 11) % 41 - 20 for step in range(12)]
        for target in (-25, -3, 0, 4, 30):
            assert count_triples(numbers, target) == by_listing(numbers, target), (
                seed,
                target,
            )


def test_counts_over_a_thousand_million_triples() -> None:
    """Returns a count far too large to have been reached one triple at a time.

    Two thousand zeros: every one of the 1,331,334,000 triples sums to zero.
    """
    numbers = [0] * 2_000

    assert count_triples(numbers, 1) == comb(2_000, 3)
    assert count_triples(numbers, 0) == 0


def test_handles_two_thousand_mixed_values() -> None:
    """Counts across a thousand -1s and a thousand +1s.

    A triple sums below zero when it has two or three of the -1s. Those can
    be counted by choosing: three from the thousand, or two from the
    thousand and one of the others.
    """
    numbers = [1 if position % 2 else -1 for position in range(2_000)]

    assert count_triples(numbers, 0) == comb(1_000, 3) + comb(1_000, 2) * 1_000
