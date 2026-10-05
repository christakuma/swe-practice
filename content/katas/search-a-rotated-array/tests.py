"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import search


def test_finds_a_value_in_the_rotated_tail() -> None:
    """Finds a target that sits after the rotation point."""
    assert search([4, 5, 6, 7, 0, 1, 2], 0) == 4


def test_finds_a_value_in_the_rotated_head() -> None:
    """Finds a target that sits before the rotation point."""
    assert search([4, 5, 6, 7, 0, 1, 2], 6) == 2


def test_reports_an_absent_value() -> None:
    """Returns -1 for a value that is not present."""
    assert search([4, 5, 6, 7, 0, 1, 2], 3) == -1


def test_handles_an_empty_list() -> None:
    """Returns -1 for an empty list without raising."""
    assert search([], 5) == -1


def test_handles_a_single_element() -> None:
    """Finds or rejects the only value in a one-element list."""
    assert search([1], 1) == 0
    assert search([1], 0) == -1


def test_classifies_the_sorted_half_at_a_window_of_two() -> None:
    """Finds the target in a two-element rotated list.

    The smallest case that separates `numbers[low] <= numbers[mid]` from the
    strict version: `mid` rounds down to `low`, so the two are the same
    element, and `<` wrongly concludes the left half is unsorted and discards
    the half holding the answer. Verified against that bug, which returns -1
    here and passes every other hand-picked case in this file.
    """
    assert search([1, 0], 0) == 1
    assert search([1, 0], 1) == 0


def test_handles_a_list_that_was_not_rotated() -> None:
    """Searches a fully sorted list, which is a rotation of zero."""
    assert search([1, 2, 3, 4, 5], 1) == 0
    assert search([1, 2, 3, 4, 5], 5) == 4
    assert search([1, 2, 3, 4, 5], 3) == 2
    assert search([1, 2, 3, 4, 5], 6) == -1


def test_finds_the_values_at_both_ends() -> None:
    """Finds the first and last elements of a rotated list."""
    numbers = [5, 6, 7, 1, 2, 3, 4]

    assert search(numbers, 5) == 0
    assert search(numbers, 4) == 6


def test_rejects_values_outside_the_range() -> None:
    """Returns -1 for values below the minimum and above the maximum."""
    numbers = [4, 5, 6, 7, 0, 1, 2]

    assert search(numbers, -1) == -1
    assert search(numbers, 8) == -1


def test_handles_negative_values() -> None:
    """Searches a rotated list whose values straddle zero."""
    numbers = [3, 7, -9, -4, 0]

    assert search(numbers, -9) == 2
    assert search(numbers, 3) == 0
    assert search(numbers, -5) == -1


def test_finds_every_value_for_every_rotation_at_every_small_size() -> None:
    """Finds every present value, for every rotation, at every size up to forty.

    Around twenty thousand searches. The comparison bug, the off-by-one window
    updates and the mis-scoped range checks each fail only at particular
    (size, rotation, target) triples, so enumerating beats choosing.
    """
    for size in range(1, 41):
        base = [value * 3 - 7 for value in range(size)]
        for k in range(size):
            rotated = base[k:] + base[:k]
            for index, value in enumerate(rotated):
                assert search(rotated, value) == index, (rotated, value)


def test_rejects_every_absent_value_for_every_rotation() -> None:
    """Returns -1 for values in the gaps, at every size and rotation.

    The values step by three, so every `value + 1` is absent. A search that
    settles into the wrong half tends to return an index rather than -1.
    """
    for size in range(1, 31):
        base = [value * 3 - 7 for value in range(size)]
        absent = [value + 1 for value in base] + [base[0] - 1, base[-1] + 1]
        for k in range(size):
            rotated = base[k:] + base[:k]
            for value in absent:
                assert search(rotated, value) == -1, (rotated, value)


def test_leaves_the_input_alone() -> None:
    """Does not sort or mutate the list it was given."""
    numbers = [4, 5, 6, 7, 0, 1, 2]
    original = list(numbers)

    search(numbers, 0)

    assert numbers == original


def test_searches_a_large_list() -> None:
    """Finds and rejects values in a list of two million elements."""
    size = 2_000_000
    pivot = 1_234_567
    base = list(range(0, size * 2, 2))
    rotated = base[pivot:] + base[:pivot]

    assert rotated[search(rotated, 0)] == 0
    assert rotated[search(rotated, base[-1])] == base[-1]
    assert search(rotated, 1) == -1
