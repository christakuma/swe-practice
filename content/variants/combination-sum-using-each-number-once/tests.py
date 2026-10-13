"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import combination_sum


def by_subsets(candidates: list[int], target: int) -> list[tuple[int, ...]]:
    """Try every subset of positions and keep the distinct ones that fit."""
    found = {
        tuple(sorted(candidates[position] for position in positions))
        for size in range(len(candidates) + 1)
        for positions in combinations(range(len(candidates)), size)
        if sum(candidates[position] for position in positions) == target
    }
    return sorted(found)


def test_returns_the_documented_combinations() -> None:
    """Returns the combinations of the worked example."""
    assert combination_sum([10, 1, 2, 7, 6, 1, 5], 8) == [
        (1, 1, 6),
        (1, 2, 5),
        (1, 7),
        (2, 6),
    ]


def test_does_not_use_a_candidate_twice() -> None:
    """Uses each candidate at most once."""
    assert combination_sum([3], 6) == []
    assert combination_sum([2, 3], 4) == []


def test_uses_a_repeated_value_as_often_as_it_appears() -> None:
    """Uses a value twice when the list holds it twice, and no more."""
    assert combination_sum([2, 2], 4) == [(2, 2)]
    assert combination_sum([2, 2], 6) == []
    assert combination_sum([2, 5, 2, 1, 2], 5) == [(1, 2, 2), (5,)]


def test_lists_a_combination_once_whichever_copies_it_uses() -> None:
    """Returns one entry when equal candidates could each supply it."""
    assert combination_sum([1, 1, 2], 3) == [(1, 2)]
    assert combination_sum([1, 1, 1, 2, 2], 3) == [(1, 1, 1), (1, 2)]


def test_returns_the_empty_combination_for_a_target_of_zero() -> None:
    """Returns the single empty combination for a target of zero."""
    assert combination_sum([1, 2], 0) == [()]
    assert combination_sum([], 0) == [()]


def test_returns_nothing_when_nothing_fits() -> None:
    """Returns an empty list when no combination sums to the target."""
    assert combination_sum([], 5) == []
    assert combination_sum([4, 6], 5) == []


def test_returns_sorted_tuples_in_sorted_order() -> None:
    """Returns each combination ascending, and the list ascending."""
    result = combination_sum([5, 3, 4, 1, 2], 6)

    assert result == [(1, 2, 3), (1, 5), (2, 4)]
    assert all(isinstance(combination, tuple) for combination in result)


def test_agrees_with_trying_every_subset() -> None:
    """Matches a search over every subset, for every short list over 1..4."""
    for length in range(6):
        for chosen in product(range(1, 5), repeat=length):
            candidates = list(chosen)
            for target in range(9):
                expected = by_subsets(candidates, target)
                assert combination_sum(candidates, target) == expected, (
                    candidates,
                    target,
                )


def test_leaves_the_candidates_alone() -> None:
    """Does not sort or modify the caller's list."""
    candidates = [3, 1, 2]

    combination_sum(candidates, 3)

    assert candidates == [3, 1, 2]


def test_does_not_explore_every_subset_of_equal_candidates() -> None:
    """Handles thirty equal candidates within the time limit.

    Thirty 1s and a target of 15 have exactly one answer. A search that tries
    every copy at every depth and removes the duplicates afterwards visits
    155 million subsets on the way to it.
    """
    assert combination_sum([1] * 30, 15) == [(1,) * 15]
