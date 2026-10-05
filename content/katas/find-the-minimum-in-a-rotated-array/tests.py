"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import find_minimum


def rotations(values: list[int]) -> list[list[int]]:
    """Every left rotation of `values`."""
    return [values[k:] + values[:k] for k in range(len(values))]


def test_finds_the_minimum_after_a_rotation() -> None:
    """Finds the smallest value in a rotated list."""
    assert find_minimum([3, 4, 5, 1, 2]) == 1
    assert find_minimum([4, 5, 6, 7, 0, 1, 2]) == 0


def test_handles_a_list_that_was_not_rotated() -> None:
    """Returns the first element when the rotation is zero.

    A solution that compares the middle with `numbers[low]` instead of
    `numbers[high]` reads an unrotated list as if the step-down were to the
    right, and walks off toward the largest value.
    """
    assert find_minimum([11, 13, 15, 17]) == 11
    assert find_minimum([1, 2, 3, 4, 5, 6, 7, 8]) == 1


def test_handles_a_single_element() -> None:
    """Returns the only value in a one-element list."""
    assert find_minimum([1]) == 1


def test_handles_two_elements_either_way_round() -> None:
    """Handles both arrangements of a two-element list.

    The window of width two is where `low = mid` instead of `low = mid + 1`
    stops making progress and the search hangs rather than answering wrongly.
    """
    assert find_minimum([1, 2]) == 1
    assert find_minimum([2, 1]) == 1


def test_handles_the_minimum_at_the_very_end() -> None:
    """Finds the minimum when the rotation puts it in the last position."""
    assert find_minimum([2, 3, 4, 5, 1]) == 1


def test_handles_the_minimum_just_past_the_middle() -> None:
    """Finds the minimum sitting immediately right of the midpoint.

    `high = mid - 1` written for symmetry with the other branch steps over the
    answer exactly here.
    """
    assert find_minimum([4, 5, 6, 1, 2, 3]) == 1
    assert find_minimum([5, 6, 7, 8, 1, 2, 3, 4]) == 1


def test_handles_negative_values() -> None:
    """Finds the minimum when the values straddle zero."""
    assert find_minimum([3, 4, -5, -2, 0]) == -5
    assert find_minimum([-9, -4, 0, 7]) == -9


def test_finds_the_minimum_for_every_rotation_at_every_small_size() -> None:
    """Agrees for every size up to forty and every rotation of it.

    Eight hundred cases. Every known failure of this kata -- the unrotated
    list, the off-by-one that discards the answer, the branch that fails to
    narrow -- lives at a particular (size, rotation) pair, and enumerating
    them is cheaper than arguing about which pairs are dangerous.
    """
    for size in range(1, 41):
        base = [value * 3 - 7 for value in range(size)]
        for rotated in rotations(base):
            assert find_minimum(rotated) == base[0], rotated


def test_leaves_the_input_alone() -> None:
    """Does not sort or mutate the list it was given."""
    numbers = [3, 4, 5, 1, 2]
    original = list(numbers)

    find_minimum(numbers)

    assert numbers == original


def test_searches_a_large_list_in_logarithmic_time() -> None:
    """Finds the minimum in a list of two million values.

    A linear scan also answers this and the time limit is generous, so this is
    about the answer rather than the bound -- an index arithmetic error that
    only shows up past a few thousand elements shows up here.
    """
    size = 2_000_000
    pivot = 1_234_567
    base = list(range(size))
    rotated = base[pivot:] + base[:pivot]

    assert find_minimum(rotated) == 0
