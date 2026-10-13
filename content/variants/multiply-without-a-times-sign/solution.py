"""Reference solution. CI asserts this passes every test in `tests.py`."""

WORD_BITS = 32
MASK = (1 << WORD_BITS) - 1
INT_MAX = (1 << (WORD_BITS - 1)) - 1
INT_MIN = ~INT_MAX


def _add(x: int, y: int) -> int:
    """The 32-bit sum of two words, as an unsigned word."""
    while y:
        x, y = x ^ y, ((x & y) << 1) & MASK
    return x


def multiply(a: int, b: int) -> int:
    """Return `a * b` as 32-bit two's complement arithmetic, without * + or -.

    Long multiplication in base two. Each bit of `b` selects a row that is
    either nothing or `a` shifted left by that bit's position, and the rows
    are summed with the XOR-and-carry adder. `a` is masked as it shifts, so
    bits that leave the word are gone rather than making the number wider.

    Signs need no handling at all. Two's complement is arithmetic modulo
    2**32, and the low 32 bits of a product depend only on the low 32 bits of
    its factors -- so the masked patterns multiply to the right pattern
    whatever signs they stood for. Only the last line knows about signs: a
    word above `INT_MAX` has its top bit set, and `~(word ^ MASK)` is the
    negative number that pattern means.
    """
    a &= MASK
    b &= MASK
    word = 0
    while b:
        if b & 1:
            word = _add(word, a)
        a = (a << 1) & MASK
        b >>= 1
    return word if word <= INT_MAX else ~(word ^ MASK)
