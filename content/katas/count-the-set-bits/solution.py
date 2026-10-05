"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_bits(n: int) -> int:
    """Return the number of 1 bits in the binary representation of `n`.

    Brian Kernighan's trick. `n - 1` flips the lowest set bit to 0 and turns
    every 0 below it into a 1, so `n` and `n - 1` agree strictly above that bit
    and disagree from it down -- which means `n & (n - 1)` is exactly `n` with
    its lowest set bit cleared.

    So the loop runs once per *set* bit rather than once per bit. On 2**60 that
    is one iteration instead of sixty-one, and on a sparse integer of any width
    the difference is the whole cost.

    The shift-and-test loop is the honest first version and is `O(bits)`:

        while n:
            total += n & 1
            n >>= 1

    Both are correct. This one is written the way it is because the identity it
    rests on -- that subtracting 1 borrows through the trailing zeros -- is the
    reusable part, and it shows up again in "is this a power of two?"
    (`n & (n - 1) == 0`) and in isolating the lowest set bit (`n & -n`).
    """
    total = 0
    while n:
        n &= n - 1
        total += 1
    return total
