"""Reference solution. CI asserts this passes every test in `tests.py`."""

WORD_BITS = 32
MASK = (1 << WORD_BITS) - 1
INT_MAX = (1 << (WORD_BITS - 1)) - 1
INT_MIN = ~INT_MAX


def add(a: int, b: int) -> int:
    """Return `a + b` as 32-bit two's complement arithmetic, without + or -.

    Start from adding two single bits: the answer's low bit is `a ^ b` and the
    bit that spills into the next column is `a & b`. Both halves generalise to
    whole words at once -- `a ^ b` is the sum with every carry discarded, and
    `(a & b) << 1` is precisely the discarded carries, already shifted into the
    column they belong in. So addition becomes "add the carry-less sum to the
    carries", applied until there are no carries left.

    It terminates because each round moves every carry strictly one place left,
    so after at most WORD_BITS rounds there is nothing left inside the word.

    **The masking is the kata, not boilerplate.** In C the carries fall off the
    end of a 32-bit register and vanish, which is what makes the loop finish
    and what makes overflow wrap. Python integers are unbounded: nothing falls
    off, a carry out of bit 31 just makes the number wider, and on negative
    inputs -- whose Python representation has infinitely many leading sign bits
    -- `b` never reaches zero and the loop never ends. `& MASK` each round is
    what restores the finite word the algorithm assumes.

    The return is the other half of the same problem. After the loop, `a` is a
    32-bit *pattern*, not a Python number. If its top bit is set the pattern
    means a negative value, and Python will not interpret it that way on its
    own. `~(a ^ MASK)` performs the reinterpretation using only permitted
    operators: `a ^ MASK` flips every bit inside the word, and `~` of that is
    the negative number with the same two's complement bits. For `0xFFFFFFFF`
    it gives -1; for `0xFFFFFFFE`, -2.
    """
    a &= MASK
    b &= MASK
    while b:
        carry = (a & b) << 1
        a = (a ^ b) & MASK
        b = carry & MASK
    return a if a <= INT_MAX else ~(a ^ MASK)
