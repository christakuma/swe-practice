"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_palindromic_subsequence(text: str) -> int:
    """Return the length of the longest palindromic subsequence of `text`.

    `best[end]` is the answer for the stretch from `start` to `end`. If the
    two end characters match they wrap the best palindrome strictly between
    them; otherwise one of them is left out. Going through `start` from the
    back means the row for `start + 1` is the one just computed, so a single
    previous row is all that is kept.
    """
    size = len(text)
    below = [0] * size
    for start in range(size - 1, -1, -1):
        best = [0] * size
        best[start] = 1
        for end in range(start + 1, size):
            if text[start] == text[end]:
                best[end] = below[end - 1] + 2
            else:
                best[end] = max(below[end], best[end - 1])
        below = best
    return below[size - 1] if size else 0
