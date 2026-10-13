"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement

from solution import contains


def test_finds_a_value_that_is_present() -> None:
    """Reports True for a value in the list."""
    assert contains([2, 5, 6, 0, 0, 1, 2], 0) is True
    assert contains([2, 5, 6, 0, 0, 1, 2], 6) is True


def test_rejects_a_value_that_is_absent() -> None:
    """Reports False for a value not in the list."""
    assert contains([2, 5, 6, 0, 0, 1, 2], 3) is False


def test_cannot_be_fooled_by_equal_ends_and_middle() -> None:
    """Finds a value hidden where both ends and the middle are equal."""
    assert contains([1, 0, 1, 1, 1], 0) is True
    assert contains([1, 1, 1, 0, 1], 0) is True
    assert contains([1, 1, 1, 1, 1], 0) is False


def test_handles_short_lists() -> None:
    """Handles an empty list, one value and two values."""
    assert contains([], 5) is False
    assert contains([5], 5) is True
    assert contains([5], 4) is False
    assert contains([3, 1], 1) is True


def test_agrees_with_membership_for_every_small_rotated_list() -> None:
    """Matches a plain membership test for every rotation of every short list.

    Every non-decreasing list of up to seven values over 0..3, at every
    rotation, against every target from -1 to 4.
    """
    for length in range(1, 8):
        for chosen in combinations_with_replacement(range(4), length):
            ordered = list(chosen)
            for turn in range(length):
                numbers = ordered[turn:] + ordered[:turn]
                for target in range(-1, 5):
                    assert contains(numbers, target) is (target in numbers), (
                        numbers,
                        target,
                    )


def test_leaves_the_list_alone() -> None:
    """Does not sort or modify the list it was given."""
    numbers = [3, 3, 1, 2]

    contains(numbers, 2)

    assert numbers == [3, 3, 1, 2]


def test_searches_a_large_list_many_times() -> None:
    """Runs three thousand searches of two million values in the time limit.

    The values are distinct here, so every search can halve its way down.
    Scanning the list for each one reads six billion values.
    """
    size = 2_000_000
    turn = 1_234_567
    numbers = list(range(turn, size)) + list(range(turn))

    for probe in range(1500):
        assert contains(numbers, probe * 1333) is True
        assert contains(numbers, -1 - probe) is False
