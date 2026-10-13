"""Reference solution. CI asserts this passes every test in `tests.py`."""


def next_with_same_bits(n: int) -> int:
    """Return the next larger integer with as many 1 bits as `n`.

    Find the lowest block of 1s. To make the number larger by as little as
    possible, the top 1 of that block moves up one place, and the rest of the
    block falls to the bottom of the number.

    `lowest` is the block's bottom bit. Adding it makes the block carry: its
    1s become 0s and the 0 above becomes 1, which is the move up. `n ^ ripple`
    has a 1 in every bit that changed -- the block and the bit above it, two
    more bits than the 1s that still need to be put back. Shifting right by
    two drops the surplus, and dividing by `lowest` slides what is left down
    to bit zero.
    """
    lowest = n & -n
    ripple = n + lowest
    return ripple | ((n ^ ripple) >> 2) // lowest
