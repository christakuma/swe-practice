"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_distinct_palindromes(text: str) -> int:
    """Count the different palindromic substrings of `text`.

    Every palindrome has a centre -- a character or a gap between two -- and
    expanding outwards from each of the `2n - 1` centres visits each
    palindromic substring exactly once by position. Putting the substrings in
    a set collapses the repeats.
    """
    found: set[str] = set()
    for centre in range(2 * len(text) - 1):
        low = centre // 2
        high = low + centre % 2
        while low >= 0 and high < len(text) and text[low] == text[high]:
            found.add(text[low : high + 1])
            low -= 1
            high += 1
    return len(found)
