"""Reference solution. CI asserts this passes every test in `tests.py`."""

WORD_BITS = 32
MASK = (1 << WORD_BITS) - 1
INT_MAX = (1 << (WORD_BITS - 1)) - 1
INT_MIN = ~INT_MAX


def _add(x: int, y: int) -> int:
    """The 32-bit sum of two words, as an unsigned word."""
    x &= MASK
    y &= MASK
    while y:
        x, y = x ^ y, ((x & y) << 1) & MASK
    return x


def subtract(a: int, b: int) -> int:
    """Return `a - b` as 32-bit two's complement arithmetic, without + or -.

    Subtracting is adding the negative, and the two's-complement negative of
    `b` is `~b` plus one. Both additions go through the XOR-and-carry adder,
    masked to the word, so the wrap is the adder's own.

    The last line turns an unsigned word back into a signed value: anything
    above `INT_MAX` has its top bit set, and `~(word ^ MASK)` is the negative
    number that bit pattern stands for.
    """
    word = _add(a, _add(~b, 1))
    return word if word <= INT_MAX else ~(word ^ MASK)
