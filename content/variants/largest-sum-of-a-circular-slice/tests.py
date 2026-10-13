"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import max_slice_sum


def every_slice(numbers: list[int]) -> int:
    """The best sum over every start and every length, by brute force."""
    size = len(numbers)
    doubled = numbers + numbers
    return max(
        sum(doubled[start : start + length])
        for start in range(size)
        for length in range(1, size + 1)
    )


def test_wraps_when_wrapping_is_better() -> None:
    """Takes a slice that runs off the end and continues from the start."""
    assert max_slice_sum([5, -3, 5]) == 10


def test_does_not_wrap_when_it_does_not_help() -> None:
    """Takes an ordinary slice when wrapping would only add losses."""
    assert max_slice_sum([1, -2, 3, -2]) == 3


def test_wraps_across_a_loss_worth_paying() -> None:
    """Wraps through a negative value to join two gains."""
    assert max_slice_sum([3, -1, 2, -1]) == 4


def test_returns_the_least_negative_value_when_all_are_negative() -> None:
    """Returns the least negative value, never an empty slice's 0."""
    assert max_slice_sum([-3, -2, -3]) == -2
    assert max_slice_sum([-5]) == -5


def test_takes_the_whole_list_at_most_once() -> None:
    """Uses each position at most once, even when every value is a gain."""
    assert max_slice_sum([1, 2, 3]) == 6
    assert max_slice_sum([4]) == 4


def test_handles_zeros() -> None:
    """Handles zeros, including a list of nothing else."""
    assert max_slice_sum([0, 0, 0]) == 0
    assert max_slice_sum([-1, 0, -1]) == 0


def test_agrees_with_brute_force_on_every_small_list() -> None:
    """Matches an every-slice search for every list of up to six values."""
    for length in range(1, 7):
        for chosen in product(range(-2, 3), repeat=length):
            numbers = list(chosen)
            assert max_slice_sum(numbers) == every_slice(numbers), numbers


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    numbers = [2, -1, 2]

    max_slice_sum(numbers)

    assert numbers == [2, -1, 2]


def test_handles_a_hundred_thousand_values() -> None:
    """Handles a hundred thousand values within the time limit.

    All ones with a single large loss in the middle: the best slice is
    everything except that value, which is only reachable by wrapping.
    """
    numbers = [1] * 100_000
    numbers[50_000] = -1000

    assert max_slice_sum(numbers) == 99_999
