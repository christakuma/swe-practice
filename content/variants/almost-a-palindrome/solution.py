"""Reference solution. CI asserts this passes every test in `tests.py`."""


def is_almost_palindrome(text: str) -> bool:
    """Return whether `text` is a palindrome after deleting at most one
    character.

    Two pointers move inward while the ends agree. At the first disagreement
    the deletion, if there is one, must be one of those two characters:
    everything outside them already mirrors, so removing anything out there
    would misalign a pair that currently matches. That leaves two candidates
    and each is checked by an ordinary palindrome scan of what lies between.

    Both are tried, with `or`. Choosing one side by looking a character ahead
    is the well-known wrong shortcut: either side can be the one that works.
    """

    def mirrors(low: int, high: int) -> bool:
        while low < high:
            if text[low] != text[high]:
                return False
            low += 1
            high -= 1
        return True

    low, high = 0, len(text) - 1
    while low < high:
        if text[low] != text[high]:
            return mirrors(low + 1, high) or mirrors(low, high - 1)
        low += 1
        high -= 1
    return True
