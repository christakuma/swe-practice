"""Your solution goes here. The tests import from this module."""

WORD_BITS = 32
MASK = (1 << WORD_BITS) - 1
INT_MAX = (1 << (WORD_BITS - 1)) - 1
INT_MIN = ~INT_MAX


def subtract(a: int, b: int) -> int:
    """Return `a - b` as 32-bit two's complement arithmetic, without + or -.

    Args:
        a: an integer in `INT_MIN..INT_MAX`.
        b: an integer in `INT_MIN..INT_MAX`.

    Returns:
        The 32-bit wrapped difference, in `INT_MIN..INT_MAX`.
    """
    raise NotImplementedError
