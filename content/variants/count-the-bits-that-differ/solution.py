"""Reference solution. CI asserts this passes every test in `tests.py`."""


def hamming_distance(a: int, b: int) -> int:
    """Return the number of bit positions at which `a` and `b` differ.

    `a ^ b` has a 1 exactly where the two disagree, so the question becomes
    the standard one: count the set bits. `x &= x - 1` clears the lowest set
    bit each time round, so the loop runs once per differing position rather
    than once per bit of width.
    """
    differing = a ^ b
    count = 0
    while differing:
        differing &= differing - 1
        count += 1
    return count
