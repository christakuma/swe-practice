"""Reference solution. CI asserts this passes every test in `tests.py`."""


def find_missing(numbers: list[int]) -> tuple[int, int]:
    """Return the two values from 0..len(numbers) + 1 that are not present.

    XOR-ing the whole range against the whole list cancels every value that
    is present and leaves `a ^ b`, the two missing values folded together.
    That cannot be unfolded directly -- but it is non-zero, and any 1 bit in
    it marks a position where `a` and `b` differ.

    So that bit sorts the numbers into two groups with one missing value in
    each, and the single-missing trick recovers one of them from its group.
    The other falls out of `a ^ b`. `x & -x` isolates the lowest set bit.
    """
    top = len(numbers) + 1
    both = 0
    for value in range(top + 1):
        both ^= value
    for value in numbers:
        both ^= value

    bit = both & -both
    first = 0
    for value in range(top + 1):
        if value & bit:
            first ^= value
    for value in numbers:
        if value & bit:
            first ^= value

    second = both ^ first
    return (first, second) if first < second else (second, first)
