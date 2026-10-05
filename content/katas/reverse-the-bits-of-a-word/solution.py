"""Reference solution. CI asserts this passes every test in `tests.py`."""

WORD_BITS = 32


def reverse_bits(n: int) -> int:
    """Reverse the bits of `n` read as a 32-bit unsigned word.

    Take the lowest bit of the input and push it onto the high end of the
    result. Because `result` is shifted left *before* each write, it grows from
    the bottom up -- so the first bit read is pushed furthest left by the
    thirty-one shifts that follow it, and the last bit read ends up at position
    zero. That is the reversal, and it needs no indexing arithmetic.

    The loop runs exactly `WORD_BITS` times and not `while n`. This is the
    whole difficulty of the problem in Python: the leading zeros of a 32-bit
    word are *part of the word*, and reversing moves them into the low
    positions. `while n` stops as soon as the input is exhausted and leaves the
    result unshifted by however many leading zeros there were, so `1` comes
    back as `1` instead of `2**31`. Nothing in the language will tell you the
    width -- the problem statement is the only place it exists.

    A fixed trip count is also why this is O(1) rather than O(bits): the cost
    does not depend on the input at all.
    """
    result = 0
    for _ in range(WORD_BITS):
        result = (result << 1) | (n & 1)
        n >>= 1
    return result
