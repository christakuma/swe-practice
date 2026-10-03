"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import move_zeroes


def test_moves_zeroes_to_the_end() -> None:
    """Moves the zeros to the end."""
    numbers = [0, 1, 0, 3, 12]

    move_zeroes(numbers)

    assert numbers == [1, 3, 12, 0, 0]


def test_keeps_the_order_of_the_non_zeroes() -> None:
    """Leaves the non-zero elements in their original relative order.

    A solution that swaps each zero with the last element is fast, in place,
    and returns [4, 1, 3, 0, 0] here.
    """
    numbers = [1, 0, 3, 0, 4]

    move_zeroes(numbers)

    assert numbers == [1, 3, 4, 0, 0]


def test_modifies_the_list_it_was_given() -> None:
    """Works in place rather than returning a new list.

    The function returns None, so a solution that builds a new list has no way
    to communicate it -- and this is the test that says so out loud.
    """
    numbers = [0, 5]

    assert move_zeroes(numbers) is None
    assert numbers == [5, 0]


def test_handles_a_list_with_no_zeroes() -> None:
    """Leaves a list with no zeros unchanged."""
    numbers = [1, 2, 3]

    move_zeroes(numbers)

    assert numbers == [1, 2, 3]


def test_handles_a_list_of_only_zeroes() -> None:
    """Leaves a list of only zeros unchanged."""
    numbers = [0, 0, 0]

    move_zeroes(numbers)

    assert numbers == [0, 0, 0]


def test_handles_an_empty_list() -> None:
    """Does nothing to an empty list."""
    numbers: list[int] = []

    move_zeroes(numbers)

    assert numbers == []


def test_handles_negative_numbers() -> None:
    """Treats negative numbers as ordinary non-zero values."""
    numbers = [0, -1, 0, -2]

    move_zeroes(numbers)

    assert numbers == [-1, -2, 0, 0]


def test_handles_a_long_list_quickly() -> None:
    """Rearranges a list far too long for repeated shifting.

    Fifty thousand elements, alternating. A solution that removes each zero and
    appends it -- or inserts at the end with `list.pop(i)` -- is quadratic,
    because every removal shifts the tail.
    """
    numbers = [0, 7] * 25_000

    move_zeroes(numbers)

    assert numbers[:25_000] == [7] * 25_000
    assert numbers[25_000:] == [0] * 25_000
