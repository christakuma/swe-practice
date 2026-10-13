"""Reference solution. CI asserts this passes every test in `tests.py`."""


def reverse_bytes(n: int) -> int:
    """Reverse the byte order of `n` read as a 32-bit unsigned word.

    Each byte is masked out and shifted to its mirror position. Masking
    before the left shifts is what keeps the result inside 32 bits, since a
    Python integer would otherwise simply grow.
    """
    return (
        ((n & 0x000000FF) << 24)
        | ((n & 0x0000FF00) << 8)
        | ((n & 0x00FF0000) >> 8)
        | ((n & 0xFF000000) >> 24)
    )
