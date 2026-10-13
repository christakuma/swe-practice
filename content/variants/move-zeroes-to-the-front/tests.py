"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import move_zeroes


def rearranged(numbers: list[int]) -> list[int]:
    """What the list should become, built as a new list."""
    return [value for value in numbers if value == 0] + [
        value for value in numbers if value != 0
    ]


def test_moves_the_zeros_to_the_front() -> None:
    """Puts every zero ahead of every non-zero value."""
    numbers = [0, 1, 0, 3, 12]

    move_zeroes(numbers)

    assert numbers == [0, 0, 1, 3, 12]


def test_keeps_the_other_values_in_order() -> None:
    """Leaves the non-zero values in their original relative order."""
    numbers = [5, 0, 4, 0, 3, 2]

    move_zeroes(numbers)

    assert numbers == [0, 0, 5, 4, 3, 2]


def test_returns_nothing_and_changes_the_list_it_was_given() -> None:
    """Works in place and returns None."""
    numbers = [1, 0]

    assert move_zeroes(numbers) is None
    assert numbers == [0, 1]


def test_leaves_settled_lists_alone() -> None:
    """Leaves a list with no zeros, only zeros, or nothing in it unchanged."""
    for settled in ([1, 2, 3], [0, 0], [], [0, 0, 7]):
        numbers = list(settled)
        move_zeroes(numbers)
        assert numbers == settled


def test_treats_negative_numbers_as_ordinary_values() -> None:
    """Moves only zeros, not negative values."""
    numbers = [4, 0, -1, 0]

    move_zeroes(numbers)

    assert numbers == [0, 0, 4, -1]


def test_agrees_with_building_a_new_list() -> None:
    """Matches a rebuilt list for every short list over -1..2."""
    for length in range(7):
        for chosen in product(range(-1, 3), repeat=length):
            numbers = list(chosen)
            move_zeroes(numbers)
            assert numbers == rearranged(list(chosen)), chosen


def test_rearranges_a_long_list() -> None:
    """Rearranges 300,000 values within the time limit.

    Alternating values and zeros, so half the list has to move. Lifting each
    zero out and inserting it at the front shifts the whole list every time.
    """
    size = 300_000
    numbers = [index if index % 2 else 0 for index in range(size)]

    move_zeroes(numbers)

    assert numbers[: size // 2] == [0] * (size // 2)
    assert numbers[size // 2 :] == list(range(1, size, 2))
