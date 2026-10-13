"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_slice(numbers: list[int], target: int) -> int:
    """Return the length of the longest slice that adds up to `target`.

    A slice sums to the target exactly when the prefix sum at its end exceeds
    the prefix sum at its start by the target. So at each position the
    question is whether `prefix - target` has been a prefix sum before -- and,
    for the longest slice, how far back it *first* was.

    `first_seen` therefore records each prefix sum once, at its earliest
    position, and is never updated afterwards. The counting version of this
    problem keeps a tally in the same dict; the only change is what is stored
    and that later sightings are ignored.

    The entry for 0 at position 0 is the empty prefix. It is what lets a
    slice start at the beginning of the list.
    """
    first_seen = {0: 0}
    longest = 0
    prefix = 0
    for position, value in enumerate(numbers, start=1):
        prefix += value
        start = first_seen.get(prefix - target)
        if start is not None:
            longest = max(longest, position - start)
        first_seen.setdefault(prefix, position)
    return longest
