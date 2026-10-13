"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import max_slice_sum


def by_trying_everything(numbers: list[int]) -> int:
    """Every slice, whole and with each one of its elements removed in turn."""
    sums = []
    for start in range(len(numbers)):
        for end in range(start + 1, len(numbers) + 1):
            piece = numbers[start:end]
            sums.append(sum(piece))
            if len(piece) > 1:
                sums.extend(sum(piece) - value for value in piece)
    return max(sums)


def test_drops_a_negative_between_two_positives() -> None:
    """Joins two stretches across a single negative value."""
    assert max_slice_sum([1, -2, 0, 3]) == 4
    assert max_slice_sum([5, -9, 6]) == 11


def test_does_not_drop_two() -> None:
    """Does not join stretches separated by two unwanted values."""
    assert max_slice_sum([1, -2, -2, 3]) == 3
    assert max_slice_sum([5, -9, -9, 6]) == 6


def test_dropping_is_optional() -> None:
    """Keeps every element when none of them is negative."""
    assert max_slice_sum([2, 3, 4]) == 9
    assert max_slice_sum([7]) == 7


def test_something_must_remain() -> None:
    """Returns the least negative value when every value is negative."""
    assert max_slice_sum([-1, -1, -1]) == -1
    assert max_slice_sum([-5]) == -5
    assert max_slice_sum([-3, -7]) == -3


def test_drops_the_worst_of_several_negatives() -> None:
    """Chooses which single negative to remove from a slice holding several.

    Keeping the whole of [4, -1, 5, -6, 5] and dropping the -6 gives 13.
    """
    assert max_slice_sum([4, -1, 5, -6, 5]) == 13
    assert max_slice_sum([4, -6, 5, -1, 5]) == 13


def test_the_best_plain_slice_is_not_always_the_place_to_drop() -> None:
    """Bridges two slices that the plain algorithm would keep apart.

    The best slice without dropping is the 10 alone, which has nothing to
    remove. The answer joins the 6 and the 7 across the -20, and two -30s
    keep the 10 out of reach.
    """
    assert max_slice_sum([10, -30, -30, 6, -20, 7]) == 13


def test_a_drop_at_the_edge_of_a_slice_is_just_a_shorter_slice() -> None:
    """Gains nothing by dropping the first or last element of the list."""
    assert max_slice_sum([-4, 2, 3]) == 5
    assert max_slice_sum([2, 3, -4]) == 5


def test_zero_is_worth_keeping_or_dropping_equally() -> None:
    """Handles zeros, which change nothing either way."""
    assert max_slice_sum([0, 0, 0]) == 0
    assert max_slice_sum([0, -1, 0]) == 0


def test_agrees_with_trying_everything() -> None:
    """Matches an exhaustive search for every short list.

    Every list of one to six values drawn from -4, -1, 0, 2, 5.
    """
    for size in range(1, 7):
        for chosen in product((-4, -1, 0, 2, 5), repeat=size):
            numbers = list(chosen)
            assert max_slice_sum(numbers) == by_trying_everything(numbers), numbers


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    numbers = [3, -1, 2]

    max_slice_sum(numbers)

    assert numbers == [3, -1, 2]


def test_handles_a_hundred_thousand_values() -> None:
    """Scans a hundred thousand values in one pass, within the time limit.

    Ones, with a -5 in the middle of every thousand and a single -1000 near
    the centre. Each -5 has hundreds of ones on both sides and is worth
    keeping for what it joins; the -1000 is the element to drop.
    """
    numbers = [1] * 100_000
    for position in range(500, 100_000, 1000):
        numbers[position] = -5
    numbers[50_250] = -1000

    assert max_slice_sum(numbers) == sum(numbers) + 1000
