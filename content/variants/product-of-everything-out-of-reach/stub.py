"""Your solution goes here. The tests import from this module."""


def product_except_window(numbers: list[int], k: int) -> list[int]:
    """Return, for each position, the product of everything out of its reach.

    Args:
        numbers: the values. May contain zeros and negatives.
        k: how many neighbours on each side a position also leaves out.

    Returns:
        A list the same length as `numbers`, where position i holds the
        product of every `numbers[j]` with `abs(i - j) > k`.
    """
    raise NotImplementedError
