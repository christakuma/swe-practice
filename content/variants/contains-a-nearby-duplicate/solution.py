"""Reference solution. CI asserts this passes every test in `tests.py`."""


def has_duplicate(numbers: list[int], k: int) -> bool:
    """Return whether two equal values sit at most `k` positions apart.

    A dict from each value to the position it was last seen at. For any
    position, the closest earlier copy of its value is the most recent one,
    so that is the only one worth remembering -- which is why the entry is
    overwritten on every visit rather than set once.
    """
    last_seen: dict[int, int] = {}
    for position, value in enumerate(numbers):
        if value in last_seen and position - last_seen[value] <= k:
            return True
        last_seen[value] = position
    return False
