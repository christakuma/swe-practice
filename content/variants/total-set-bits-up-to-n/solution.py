"""Reference solution. CI asserts this passes every test in `tests.py`."""


def total_bits_up_to(n: int) -> int:
    """Return the total number of set bits in every integer from 0 to `n`.

    Column by column rather than number by number. Down bit position `i`, the
    numbers 0, 1, 2, ... repeat a cycle of `2**i` zeros then `2**i` ones. The
    `n + 1` numbers in play contain some whole cycles, each contributing
    `2**i` ones, and a remainder, which contributes however far it reaches
    into the ones half of a cycle.
    """
    count = n + 1
    total = 0
    half = 1
    while half <= n:
        cycle = half * 2
        total += (count // cycle) * half + max(count % cycle - half, 0)
        half = cycle
    return total
