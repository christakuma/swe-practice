"""Reference solution. CI asserts this passes every test in `tests.py`."""

WORD_BITS = 32
MASK = (1 << WORD_BITS) - 1


def rotate_left(n: int, k: int) -> int:
    """Rotate `n`, read as a 32-bit unsigned word, left by `k` places.

    Two shifts, one for each part of the word. Shifting left by `k` moves
    the low `32 - k` bits to their new places and pushes the top `k` bits
    out past bit 31. Shifting right by `32 - k` brings those same top `k`
    bits down to the bottom, which is where a rotation puts them.

    The mask is the width. Python integers do not overflow, so the bits the
    left shift pushes out are still there above bit 31 until they are
    removed. This is the same lesson as reversing: a 32-bit word in Python
    is a convention you keep, not a type you are given.

    The modulus makes `k` a value both shifts can use, and makes the size of
    `k` irrelevant. With `k` reduced to zero the right shift is by 32, which
    clears a 32-bit value entirely, so the result is `n` and zero needs no
    case of its own. That is a property of Python: in C, shifting a 32-bit
    value by 32 is undefined, and the idiom there is `(-k) & 31`.
    """
    k %= WORD_BITS
    return ((n << k) | (n >> (WORD_BITS - k))) & MASK
