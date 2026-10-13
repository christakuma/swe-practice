"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc
from itertools import combinations_with_replacement

from solution import merge_into

JUNK = -777


def merged(values: list[int], second: list[int], junk: int = JUNK) -> list[int]:
    """Run the merge on a first list padded with `junk`, and return it."""
    first = values + [junk] * len(second)
    result = merge_into(first, len(values), second)
    assert result is None
    return first


def test_interleaves_two_lists() -> None:
    """Merges values that alternate between the two lists."""
    assert merged([1, 2, 3], [2, 5, 6]) == [1, 2, 2, 3, 5, 6]
    assert merged([1, 4, 7], [2, 5, 8]) == [1, 2, 4, 5, 7, 8]


def test_the_second_list_goes_entirely_in_front() -> None:
    """Moves every value of the first list up when the second is all smaller.

    This is the case a front-to-back merge destroys: the first write lands on
    a value that has not been read yet.
    """
    assert merged([4, 5, 6], [1, 2, 3]) == [1, 2, 3, 4, 5, 6]
    assert merged([10], [1, 2, 3, 4]) == [1, 2, 3, 4, 10]


def test_the_second_list_goes_entirely_behind() -> None:
    """Leaves the first list's values where they are when the second is all larger."""
    assert merged([1, 2, 3], [4, 5, 6]) == [1, 2, 3, 4, 5, 6]


def test_handles_an_empty_second_list() -> None:
    """Changes nothing when there is nothing to merge in."""
    assert merged([1, 2, 3], []) == [1, 2, 3]
    assert merged([], []) == []


def test_handles_a_first_list_with_no_values() -> None:
    """Copies the second list in when the first holds only spare slots."""
    assert merged([], [3]) == [3]
    assert merged([], [1, 2, 3]) == [1, 2, 3]


def test_handles_repeated_values() -> None:
    """Keeps every copy of a value that appears in both lists."""
    assert merged([2, 2, 2], [2, 2]) == [2, 2, 2, 2, 2]
    assert merged([1, 3, 3], [3, 3, 4]) == [1, 3, 3, 3, 3, 4]


def test_does_not_rely_on_what_the_spare_slots_hold() -> None:
    """Ignores the junk in the spare slots, whatever it is.

    The junk is tried as a value below everything, above everything, and
    equal to a real value.
    """
    for junk in (-(10**9), 10**9, 0, 3):
        assert merged([1, 3, 5], [0, 3, 9], junk) == [0, 1, 3, 3, 5, 9], junk
        assert merged([], [0, 3], junk) == [0, 3], junk


def test_handles_negative_values() -> None:
    """Merges values below zero."""
    assert merged([-9, -4, 0], [-6, -4, 2]) == [-9, -6, -4, -4, 0, 2]


def test_agrees_with_sorting_on_every_small_pair() -> None:
    """Matches a sort of all the values for every pair of short sorted lists.

    Every pair of ascending lists of up to four values drawn from 0..3.
    """
    lists = [
        list(chosen)
        for size in range(5)
        for chosen in combinations_with_replacement(range(4), size)
    ]
    for values in lists:
        for second in lists:
            assert merged(values, second) == sorted(values + second), (values, second)


def test_leaves_the_second_list_alone() -> None:
    """Does not modify the list being merged in."""
    second = [2, 4]

    merged([1, 3, 5], second)

    assert second == [2, 4]


def test_keeps_the_same_list_object_and_length() -> None:
    """Writes into the list it was given without growing or replacing it."""
    first = [1, 5, JUNK, JUNK]
    identity = id(first)

    merge_into(first, 2, [2, 3])

    assert id(first) == identity
    assert first == [1, 2, 3, 5]


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the lists.

    A hundred thousand even numbers in the first list and a hundred thousand
    odd numbers in the second, so the two alternate all the way. Sorting the
    combined values needs scratch space, and merging into a fresh list needs
    all of it again. The lists are built before measuring starts.
    """
    size = 100_000
    first = list(range(0, 2 * size, 2)) + [JUNK] * size
    second = list(range(1, 2 * size, 2))

    tracemalloc.start()
    merge_into(first, size, second)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert first == list(range(2 * size))
    assert peak < 64_000, f"allocated {peak} bytes"
