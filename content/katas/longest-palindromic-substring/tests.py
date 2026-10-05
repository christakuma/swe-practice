"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_palindrome


def reference(text: str) -> str:
    """Longest palindromic substring by checking every substring.

    An independent oracle: it works from substring slices rather than centres,
    so it shares no expansion logic with the real solution. Cubic, and fine at
    these sizes.
    """
    best = ""
    for start in range(len(text)):
        for stop in range(start + 1, len(text) + 1):
            candidate = text[start:stop]
            if candidate == candidate[::-1] and len(candidate) > len(best):
                best = candidate
    return best


def test_finds_an_odd_length_palindrome() -> None:
    """Returns an odd-length palindrome from the middle of a string."""
    assert longest_palindrome("babad") == "bab"


def test_finds_an_even_length_palindrome() -> None:
    """Returns an even-length palindrome.

    The discriminating test for the whole kata: a solution that only tries
    character-centres finds nothing longer than one character here and returns
    "c". Every odd-length case above passes without even-centre handling.
    """
    assert longest_palindrome("cbbd") == "bb"
    assert longest_palindrome("abba") == "abba"


def test_handles_an_empty_string() -> None:
    """Returns an empty string for an empty input."""
    assert longest_palindrome("") == ""


def test_handles_a_single_character() -> None:
    """Returns the one character, which is a palindrome of length one."""
    assert longest_palindrome("a") == "a"


def test_handles_a_string_with_no_repeats() -> None:
    """Returns the first character when nothing longer is a palindrome."""
    assert longest_palindrome("abcde") == "a"


def test_returns_the_earliest_of_several_longest() -> None:
    """Returns the leftmost palindrome when several tie for longest.

    "aba" and "cdc" are both length three. A length comparison using >=
    instead of > replaces the first with the second.
    """
    assert longest_palindrome("abacdc") == "aba"
    assert longest_palindrome("aabb") == "aa"


def test_handles_a_whole_string_palindrome() -> None:
    """Returns the entire string when it is itself a palindrome."""
    assert longest_palindrome("racecar") == "racecar"
    assert longest_palindrome("aa") == "aa"
    assert longest_palindrome("aaa") == "aaa"


def test_handles_a_palindrome_at_either_end() -> None:
    """Finds a palindrome touching the start or the end of the string.

    Expansion has to stop at the boundary rather than reading past it.
    """
    assert longest_palindrome("abbxyz") == "bb"
    assert longest_palindrome("xyzabb") == "bb"
    assert longest_palindrome("aabcd") == "aa"
    assert longest_palindrome("dcbaa") == "aa"


def test_handles_a_uniform_string() -> None:
    """Returns the whole string when every character is the same."""
    assert longest_palindrome("aaaaaa") == "aaaaaa"


def test_handles_non_letter_characters() -> None:
    """Treats every character as significant, including punctuation and case.

    Unlike `is-it-a-palindrome`, nothing is skipped and nothing is folded.
    """
    assert longest_palindrome("a,,a") == "a,,a"
    assert longest_palindrome("Aa") == "A"
    assert longest_palindrome("1221") == "1221"


def test_agrees_with_brute_force_on_every_binary_string() -> None:
    """Matches the substring search for every string of a and b up to length ten.

    About two thousand strings. Binary alphabets maximise palindrome density,
    so the even/odd centre handling and the tie-break are under constant
    pressure.
    """
    for length in range(11):
        for characters in product("ab", repeat=length):
            text = "".join(characters)

            assert longest_palindrome(text) == reference(text), text


def test_agrees_with_brute_force_on_every_ternary_string() -> None:
    """Matches the substring search for every string of a, b and c up to length seven.

    A third character makes palindromes rarer and the "no palindrome longer
    than one" path common, which the binary sweep barely exercises.
    """
    for length in range(8):
        for characters in product("abc", repeat=length):
            text = "".join(characters)

            assert longest_palindrome(text) == reference(text), text


def test_returns_an_actual_substring() -> None:
    """Returns a slice of the input that really is a palindrome."""
    text = "forgeeksskeegfor"

    result = longest_palindrome(text)

    assert result in text
    assert result == result[::-1]
    assert result == "geeksskeeg"


def test_handles_a_long_uniform_string() -> None:
    """Searches five thousand identical characters within the time limit.

    The worst case for centre expansion -- every centre grows to the full
    width -- and the one input that separates it from enumerating every
    substring and testing each. Measured at n = 5000: centre expansion 1.6s,
    enumerate-and-test 39.0s, against a 15s limit.

    It does **not** catch either slicing mistake, and the docstring used to
    claim otherwise. Slicing a candidate once per centre is O(n^2), not cubic;
    slicing at every expansion step is cubic but CPython's slice is a memcpy,
    so even that extrapolates to only about 3s here. Both are wasteful and
    neither is
    slow enough to fail a wall-clock limit, which is why the advice to carry
    `(start, length)` is about allocation rather than about the bound.
    """
    text = "a" * 5_000

    assert longest_palindrome(text) == text


def test_finds_a_long_palindrome_buried_in_noise() -> None:
    """Finds a long palindrome surrounded by non-palindromic text."""
    buried = "abcde" * 200
    text = "xy" + buried + buried[::-1] + "zw"

    assert longest_palindrome(text) == buried + buried[::-1]
