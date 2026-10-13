"""Reference solution. CI asserts this passes every test in `tests.py`."""


def is_one_edit_away(source: str, target: str) -> bool:
    """Return whether the two strings are at most one edit apart.

    The lengths decide which edit is even possible: equal lengths allow only
    a replacement, lengths one apart only an insertion into the shorter.
    Both are then the same check -- find the first disagreement, and require
    everything after it to match, stepping over one character in both
    strings for a replacement or in the longer one alone for an insertion.

    If the common part never disagrees, the strings are equal or differ by
    one trailing character, and both slices below are empty or equal.
    """
    if abs(len(source) - len(target)) > 1:
        return False
    shorter, longer = sorted((source, target), key=len)
    at = 0
    while at < len(shorter) and shorter[at] == longer[at]:
        at += 1
    if len(shorter) == len(longer):
        return shorter[at + 1 :] == longer[at + 1 :]
    return shorter[at:] == longer[at + 1 :]
