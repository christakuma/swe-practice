"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, pairwise, product

from solution import count_longest_increasing


def by_listing(numbers: list[int]) -> int:
    """Count the increasing choices of positions at the greatest size that has any."""
    for size in range(len(numbers), 0, -1):
        found = sum(
            all(numbers[a] < numbers[b] for a, b in pairwise(positions))
            for positions in combinations(range(len(numbers)), size)
        )
        if found:
            return found
    return 1


def test_counts_two_routes_to_the_longest_length() -> None:
    """Counts each longest subsequence when there are two."""
    assert count_longest_increasing([1, 3, 5, 4, 7]) == 2


def test_a_sorted_list_has_one() -> None:
    """Returns 1 when the whole list is the only longest subsequence."""
    assert count_longest_increasing([1, 2, 3]) == 1
    assert count_longest_increasing([5]) == 1


def test_equal_values_do_not_extend_a_run() -> None:
    """Counts every position when nothing increases at all."""
    assert count_longest_increasing([2, 2, 2, 2]) == 4
    assert count_longest_increasing([9, 7, 5]) == 3


def test_equal_values_at_different_positions_are_different_choices() -> None:
    """Counts by position, so two copies of a value give two subsequences."""
    assert count_longest_increasing([1, 3, 3]) == 2
    assert count_longest_increasing([1, 1, 3]) == 2
    assert count_longest_increasing([1, 1, 3, 3]) == 4


def test_the_longest_runs_may_end_in_different_places() -> None:
    """Adds up runs that finish at different positions.

    In [1, 2, 4, 3] the two longest runs end at the 4 and at the 3. Reading
    the count from whichever position is found first gives 1.
    """
    assert count_longest_increasing([1, 2, 4, 3]) == 2
    assert count_longest_increasing([1, 5, 2, 6, 3, 7]) == 3


def test_counts_multiply_along_a_run() -> None:
    """Multiplies the choices at each stage of a run of pairs.

    Three stages, each offering two positions for its value.
    """
    assert count_longest_increasing([1, 1, 2, 2, 3, 3]) == 8
    assert count_longest_increasing([2, 1, 4, 3, 6, 5]) == 8


def test_shorter_runs_are_not_counted() -> None:
    """Leaves out increasing subsequences that are not of the greatest length."""
    assert count_longest_increasing([1, 2, 3, 0, 9]) == 1
    assert count_longest_increasing([3, 1, 2]) == 1


def test_an_empty_list_has_one_empty_subsequence() -> None:
    """Returns 1 for an empty list."""
    assert count_longest_increasing([]) == 1


def test_handles_negative_values() -> None:
    """Handles values below zero."""
    assert count_longest_increasing([-3, -1, -2, 0]) == 2


def test_agrees_with_listing_every_subsequence() -> None:
    """Matches an exhaustive count for every short list.

    Every list of up to six values drawn from 0..3.
    """
    for size in range(7):
        for chosen in product(range(4), repeat=size):
            numbers = list(chosen)
            assert count_longest_increasing(numbers) == by_listing(numbers), numbers


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    numbers = [3, 1, 2]

    count_longest_increasing(numbers)

    assert numbers == [3, 1, 2]


def test_returns_an_exact_count_for_a_long_list() -> None:
    """Returns an exact count far beyond 64 bits, for a thousand values.

    Five hundred descending pairs: 1, 0, 3, 2, 5, 4 and so on. A longest run
    takes one value from each pair, either one, so there are 2**500 of them.
    """
    numbers = [value ^ 1 for value in range(1000)]

    assert count_longest_increasing(numbers) == 2**500
