"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import product_except_self


def test_multiplies_every_other_element() -> None:
    """Returns the product of the other elements at each position."""
    assert product_except_self([1, 2, 3, 4]) == [24, 12, 8, 6]


def test_handles_one_zero() -> None:
    """Handles a single zero: every other position becomes zero.

    The case that rules out dividing a total product by each element -- the
    total is zero, so the division is either wrong or impossible.
    """
    assert product_except_self([1, 2, 0, 4]) == [0, 0, 8, 0]


def test_handles_two_zeros() -> None:
    """Handles two zeros: every position becomes zero, including theirs."""
    assert product_except_self([0, 2, 0, 4]) == [0, 0, 0, 0]


def test_handles_negative_numbers() -> None:
    """Keeps the sign right with an odd number of negatives."""
    assert product_except_self([-1, 2, -3]) == [-6, 3, -2]


def test_handles_two_elements() -> None:
    """Each position is simply the other element."""
    assert product_except_self([7, 3]) == [3, 7]


def test_handles_a_single_element() -> None:
    """Returns the empty product for a list of one."""
    assert product_except_self([5]) == [1]


def test_handles_an_empty_list() -> None:
    """Returns an empty list for no input."""
    assert product_except_self([]) == []


def test_handles_a_list_of_ones() -> None:
    """Returns all ones when every element is one."""
    assert product_except_self([1, 1, 1]) == [1, 1, 1]


def test_handles_a_long_list_quickly() -> None:
    """Handles a list far too long for a product per position.

    Twenty thousand elements. Recomputing the product of the other elements at
    each position is four hundred million multiplications; two running products
    is forty thousand. Every element is 1 so the expected answer stays readable
    and the arithmetic stays small.
    """
    size = 20_000
    result = product_except_self([1] * size)

    assert len(result) == size
    assert set(result) == {1}
