"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_pairs(numbers: list[int], target: int) -> int:
    """Return how many pairs of positions hold values adding up to `target`.

    The one-pass dict from the standard problem, holding a tally instead of a
    position. At each number, every earlier occurrence of its complement is a
    partner, so the tally for the complement is added to the total -- all of
    them at once, however many there are.

    Each pair is counted exactly once, when its later member is reached. And
    the number is recorded only after the lookup, so it is never its own
    partner: a value equal to half the target pairs with the earlier copies
    of itself and no others.
    """
    seen: dict[int, int] = {}
    pairs = 0
    for value in numbers:
        pairs += seen.get(target - value, 0)
        seen[value] = seen.get(value, 0) + 1
    return pairs
