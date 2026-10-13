"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import closest_sum


def by_every_triple(numbers: list[int], target: int) -> int:
    return min(
        (sum(triple) for triple in combinations(numbers, 3)),
        key=lambda total: (abs(total - target), total),
    )


def test_finds_the_closest_sum() -> None:
    """Returns the sum nearest the target."""
    assert closest_sum([-1, 2, 1, -4], 1) == 2


def test_returns_an_exact_match() -> None:
    """Returns the target itself when three values sum to it."""
    assert closest_sum([0, 1, 2, 4], 5) == 5
    assert closest_sum([0, 0, 0], 0) == 0


def test_handles_a_target_out_of_range() -> None:
    """Returns the smallest or largest sum for a target beyond them."""
    assert closest_sum([1, 1, 1, 0], -100) == 2
    assert closest_sum([1, 2, 3, 4], 100) == 9


def test_prefers_the_smaller_sum_on_a_tie() -> None:
    """Returns the smaller of two sums equally far from the target."""
    assert closest_sum([0, 0, 1, 3], 2) == 1
    assert closest_sum([1, 1, 1, 3], 4) == 3


def test_uses_three_different_positions() -> None:
    """Does not use one position twice."""
    assert closest_sum([5, 1, 1], 15) == 7


def test_agrees_with_trying_every_triple() -> None:
    """Matches an every-triple search for every short list and many targets."""
    for length in range(3, 6):
        for chosen in product(range(-2, 3), repeat=length):
            numbers = list(chosen)
            for target in range(-7, 8):
                expected = by_every_triple(numbers, target)
                assert closest_sum(numbers, target) == expected, (numbers, target)


def test_leaves_the_list_alone() -> None:
    """Does not sort the caller's list in place."""
    numbers = [3, 1, 2, 0]

    closest_sum(numbers, 4)

    assert numbers == [3, 1, 2, 0]


def test_searches_two_thousand_values() -> None:
    """Searches two thousand values within the time limit."""
    numbers = [value * 7 for value in range(-1000, 1000)]

    assert closest_sum(numbers, 3) == 0
    assert closest_sum(numbers, 10**6) == 7 * (999 + 998 + 997)
