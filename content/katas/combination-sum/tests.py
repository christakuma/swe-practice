"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations

from solution import combination_sum


def reference(candidates: list[int], target: int) -> list[tuple[int, ...]]:
    """Choose a count for each candidate -- an independent oracle.

    Instead of recursing on "take one more of this", it decides outright how
    many copies of each candidate to use. Different search shape, same answers,
    and it cannot share a duplicate-handling bug with the intended solution.
    """
    found: set[tuple[int, ...]] = set()
    ordered = sorted(set(candidates))

    def choose(index: int, remaining: int, taken: list[int]) -> None:
        if remaining == 0:
            found.add(tuple(taken))
            return
        if index >= len(ordered):
            return
        for count in range(remaining // ordered[index] + 1):
            choose(
                index + 1,
                remaining - count * ordered[index],
                taken + [ordered[index]] * count,
            )

    choose(0, target, [])
    return sorted(found)


def test_handles_the_worked_examples() -> None:
    """Returns the documented combinations."""
    assert combination_sum([2, 3, 6, 7], 7) == [(2, 2, 3), (7,)]
    assert combination_sum([2, 3, 5], 8) == [(2, 2, 2, 2), (2, 3, 3), (3, 5)]


def test_reuses_a_candidate() -> None:
    """Uses the same candidate more than once.

    A search that advances past each candidate after using it -- the subsets
    recursion -- cannot build (2, 2, 3) and returns only (7,).
    """
    assert combination_sum([2, 3], 4) == [(2, 2)]
    assert combination_sum([3], 9) == [(3, 3, 3)]


def test_returns_nothing_when_the_target_is_unreachable() -> None:
    """Returns an empty list when no combination sums to the target."""
    assert combination_sum([2], 1) == []
    assert combination_sum([5, 7], 3) == []
    assert combination_sum([4], 10) == []


def test_handles_a_target_of_zero() -> None:
    """Returns the single empty combination for a target of zero.

    "No ways" and "one way, which is to take nothing" are different answers,
    and the second is correct -- so this is [()], not [].
    """
    assert combination_sum([2, 3], 0) == [()]
    assert combination_sum([], 0) == [()]


def test_handles_no_candidates() -> None:
    """Returns nothing when there is nothing to choose from."""
    assert combination_sum([], 5) == []


def test_does_not_return_permutations() -> None:
    """Returns each multiset once, not once per ordering.

    (2, 3, 3) and (3, 2, 3) are the same combination. A recursion that restarts
    from index zero at each step returns every ordering separately.
    """
    result = combination_sum([2, 3], 8)

    assert result == [(2, 2, 2, 2), (2, 3, 3)]
    assert len(result) == len(set(result))


def test_returns_ascending_tuples_in_ascending_order() -> None:
    """Returns each combination sorted, and the list sorted."""
    result = combination_sum([7, 2, 6, 3], 7)

    assert result == sorted(result)
    for combination in result:
        assert list(combination) == sorted(combination)
        assert sum(combination) == 7


def test_does_not_depend_on_candidate_order() -> None:
    """Gives the same answer however the candidates are given."""
    assert combination_sum([2, 3, 6, 7], 7) == combination_sum([7, 6, 3, 2], 7)
    assert combination_sum([5, 2, 3], 8) == combination_sum([3, 5, 2], 8)


def test_handles_a_candidate_of_one() -> None:
    """Handles a candidate that divides everything.

    A 1 makes every target reachable and multiplies the answer count, which is
    where a solution without the ascending-order rule explodes combinatorially.
    """
    assert combination_sum([1], 4) == [(1, 1, 1, 1)]
    assert combination_sum([1, 2], 3) == [(1, 1, 1), (1, 2)]


def test_handles_a_candidate_equal_to_the_target() -> None:
    """Includes the single-element combination."""
    assert combination_sum([7, 2], 7) == [(7,)]
    assert (5,) in combination_sum([5, 1], 5)


def test_does_not_mutate_the_candidates() -> None:
    """Leaves the caller's list alone.

    Sorting is the right first move and `candidates.sort()` is the wrong way
    to do it.
    """
    candidates = [7, 2, 6, 3]
    before = list(candidates)

    combination_sum(candidates, 7)

    assert candidates == before


def test_agrees_with_an_independent_search_across_many_inputs() -> None:
    """Matches the count-per-candidate oracle for many candidate sets.

    Every subset of 1..7 of size up to four, crossed with every target up to
    twelve -- around a thousand cases. The ascending-order rule is the only
    thing preventing duplicates, and it fails in ways that depend on which
    candidates are present.
    """
    for target in range(13):
        for size in range(1, 5):
            for chosen in combinations([1, 2, 3, 4, 5, 6, 7], size):
                candidates = list(chosen)

                assert combination_sum(candidates, target) == reference(
                    candidates, target
                ), (candidates, target)


def test_handles_a_target_needing_a_deep_recursion() -> None:
    """Builds a long combination from a single small candidate."""
    result = combination_sum([3], 300)

    assert result == [tuple([3] * 100)]


def test_handles_a_target_with_many_combinations() -> None:
    """Enumerates a large answer set within the time limit."""
    result = combination_sum([2, 3, 5, 7], 30)

    assert all(sum(combination) == 30 for combination in result)
    assert result == sorted(result)
    assert len(result) == len(set(result))
    assert len(result) == len(reference([2, 3, 5, 7], 30))
