"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_palindrome(text: str) -> str:
    """Return the longest palindromic substring, earliest on a tie.

    Enumerating substrings and testing each one asks "is this a palindrome?"
    O(n^2) times. Turning the question around removes the test entirely: every
    palindrome **has a centre**, so grow outwards from each possible centre and
    the palindrome tells you where it ends.

    The detail that is easy to miss is that there are **two kinds of centre**.
    An odd-length palindrome like `aba` is centred on a character; an
    even-length one like `abba` is centred on the gap between two. Trying only
    the first finds no even-length answer at all -- and `cbbd` is then reported
    as `c`, which is the single most common failure here. 2n - 1 centres,
    not n.

    The best answer is carried as a `(start, length)` pair and sliced once at
    the end. Slicing a candidate at every centre to compare lengths would turn
    each O(1) bookkeeping step into an O(n) copy, making the whole thing O(n^3)
    -- the bound the enumeration approach was supposed to beat.

    `>` rather than `>=` when comparing lengths is what delivers "earliest on a
    tie": centres are visited left to right, so a later equal-length palindrome
    never displaces an earlier one.

    The empty string needs no branch: no centre exists, the loop does not run,
    and slicing `(0, 0)` gives "".
    """

    def expand(low: int, high: int) -> tuple[int, int]:
        """Grow outwards while the ends match; return (start, length)."""
        while low >= 0 and high < len(text) and text[low] == text[high]:
            low -= 1
            high += 1
        # The loop exits one step past the match, so step back in.
        return low + 1, high - low - 1

    best_start, best_length = 0, 0
    for centre in range(len(text)):
        for start, length in (expand(centre, centre), expand(centre, centre + 1)):
            if length > best_length:
                best_start, best_length = start, length

    return text[best_start : best_start + best_length]
