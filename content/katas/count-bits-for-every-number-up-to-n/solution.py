"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_bits_up_to(n: int) -> list[int]:
    """Return the set-bit count of every integer from 0 to `n` inclusive.

    The observation that collapses this from O(n log n) to O(n): `i >> 1` drops
    the lowest bit of `i`, and what remains is a *smaller number whose answer
    is already in the table*. So

        bits(i) == bits(i >> 1) + (i & 1)

    -- the bits above the one you dropped, plus the one you dropped.

    That it is a single forward pass is not an accident worth glossing over:
    `i >> 1 < i` for every i >= 1, so the read is always strictly behind the
    write cursor and the table is complete where it is consulted. This is the
    smallest honest example of dynamic programming -- an ordering in which
    every subproblem is already solved -- with no memo dict and no recursion to
    obscure it.

    `bits(i) = bits(i & (i - 1)) + 1` is the equally valid alternative,
    reusing the identity from `count-the-set-bits`: clear the lowest set bit
    and you have a smaller solved number, one bit lighter. Same bound, same
    pass; this version is written with the shift because the recurrence reads
    more directly off the binary representation.
    """
    counts = [0] * (n + 1)
    for i in range(1, n + 1):
        counts[i] = counts[i >> 1] + (i & 1)
    return counts
