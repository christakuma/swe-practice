"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, combinations_with_replacement

from solution import combination_sum


def by_listing(candidates: list[int], target: int, count: int) -> list[tuple[int, ...]]:
    """Every ascending multiset of the right size, filtered by its sum."""
    return [
        chosen
        for chosen in combinations_with_replacement(sorted(candidates), count)
        if sum(chosen) == target
    ]


def test_keeps_only_combinations_of_the_right_size() -> None:
    """Returns the combinations with exactly the requested number of values."""
    assert combination_sum([2, 3, 5], 8, 3) == [(2, 3, 3)]
    assert combination_sum([2, 3, 5], 8, 2) == [(3, 5)]
    assert combination_sum([2, 3, 5], 8, 4) == [(2, 2, 2, 2)]


def test_a_shorter_combination_is_not_an_answer() -> None:
    """Rejects a combination that reaches the target with numbers to spare."""
    assert combination_sum([4], 4, 2) == []
    assert combination_sum([2, 3, 5], 8, 5) == []


def test_a_longer_combination_is_not_an_answer() -> None:
    """Rejects combinations that need more numbers than allowed."""
    assert combination_sum([1], 5, 4) == []
    assert combination_sum([2, 3, 5], 8, 1) == []


def test_reuses_a_candidate() -> None:
    """Uses one candidate several times, each use counting towards the size."""
    assert combination_sum([3], 9, 3) == [(3, 3, 3)]
    assert combination_sum([1, 2, 3], 6, 3) == [(1, 2, 3), (2, 2, 2)]


def test_returns_ascending_tuples_in_ascending_order() -> None:
    """Sorts each combination and the list of them, whatever order the input is in."""
    result = combination_sum([5, 1, 3, 2], 8, 3)

    assert result == [(1, 2, 5), (2, 3, 3)]
    assert all(isinstance(combination, tuple) for combination in result)


def test_does_not_repeat_a_combination() -> None:
    """Lists each multiset once, not once per ordering."""
    result = combination_sum([1, 2], 4, 3)

    assert result == [(1, 1, 2)]


def test_a_count_of_zero() -> None:
    """Returns the empty combination for a zero target and nothing otherwise."""
    assert combination_sum([1, 2], 0, 0) == [()]
    assert combination_sum([1, 2], 3, 0) == []


def test_a_target_of_zero_needs_a_count_of_zero() -> None:
    """Returns nothing when the target is zero but numbers must be used."""
    assert combination_sum([1, 2], 0, 2) == []


def test_agrees_with_listing_every_multiset() -> None:
    """Matches a filter over every multiset for every small input.

    Every set of one to three candidates from 1..6, every target up to 14,
    every count up to 5.
    """
    answers = 0
    for size in range(1, 4):
        for chosen in combinations(range(1, 7), size):
            candidates = list(chosen)
            for target in range(15):
                for count in range(6):
                    expected = by_listing(candidates, target, count)
                    got = combination_sum(candidates, target, count)
                    assert got == expected, (candidates, target, count)
                    answers += len(expected)
    assert answers > 500


def test_leaves_the_candidates_alone() -> None:
    """Does not modify or reorder the list it was given."""
    candidates = [5, 2, 3]

    combination_sum(candidates, 10, 3)

    assert candidates == [5, 2, 3]


def test_handles_the_widest_search() -> None:
    """Handles twenty candidates and eight numbers.

    Eight numbers from 31..50 total at least 248, so a target of 200 has no
    answer and a target of 249 has exactly one.
    """
    candidates = list(range(31, 51))

    assert combination_sum(candidates, 200, 8) == []
    assert combination_sum(candidates, 249, 8) == [(31, 31, 31, 31, 31, 31, 31, 32)]
