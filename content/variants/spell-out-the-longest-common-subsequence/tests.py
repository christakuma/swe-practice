"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import longest_common_subsequence


def is_subsequence(short: str, long: str) -> bool:
    remaining = iter(long)
    return all(character in remaining for character in short)


def best_length(first: str, second: str) -> int:
    """The longest length at which some subsequence of one is in the other."""
    for size in range(min(len(first), len(second)), -1, -1):
        for kept in set(combinations(first, size)):
            if is_subsequence("".join(kept), second):
                return size
    raise AssertionError("the empty subsequence is always shared")


def check(first: str, second: str, length: int) -> None:
    """The answer must be common to both strings and exactly `length` long."""
    found = longest_common_subsequence(first, second)

    assert isinstance(found, str)
    assert is_subsequence(found, first), (first, second, found)
    assert is_subsequence(found, second), (first, second, found)
    assert len(found) == length, (first, second, found)


def test_returns_the_shared_characters_in_order() -> None:
    """Returns the subsequence when there is only one of the greatest length."""
    assert longest_common_subsequence("abcde", "ace") == "ace"
    assert longest_common_subsequence("AGGTAB", "GXTXAYB") == "GTAB"


def test_returns_nothing_when_nothing_is_shared() -> None:
    """Returns the empty string for strings with no common character."""
    assert longest_common_subsequence("abc", "def") == ""


def test_handles_empty_strings() -> None:
    """Returns the empty string when either input is empty."""
    assert longest_common_subsequence("", "abc") == ""
    assert longest_common_subsequence("abc", "") == ""
    assert longest_common_subsequence("", "") == ""


def test_identical_strings_share_everything() -> None:
    """Returns the whole string when the two are equal."""
    assert longest_common_subsequence("banana", "banana") == "banana"


def test_one_string_inside_the_other() -> None:
    """Returns the shorter string when it is a subsequence of the longer."""
    assert longest_common_subsequence("xaxbxcx", "abc") == "abc"
    assert longest_common_subsequence("abc", "xaxbxcx") == "abc"


def test_the_answer_is_in_order_for_both_strings() -> None:
    """Does not return shared characters in an order only one string has."""
    check("ab", "ba", 1)
    check("abcd", "dcba", 1)
    check("abcbdab", "bdcaba", 4)


def test_is_not_a_greedy_match() -> None:
    """Skips an early match that would block a longer run of later ones.

    Matching the first "a" of "axbcd" against the last character of "bcda"
    uses up the whole second string for one character; the answer is "bcd".
    """
    assert longest_common_subsequence("axbcd", "bcda") == "bcd"
    assert longest_common_subsequence("bcda", "axbcd") == "bcd"


def test_handles_repeated_characters() -> None:
    """Uses a repeated character as many times as both strings allow."""
    assert longest_common_subsequence("aaa", "aa") == "aa"
    check("abab", "baba", 3)
    check("aabbaa", "ababab", 4)


def test_compares_characters_exactly() -> None:
    """Treats upper and lower case as different characters."""
    assert longest_common_subsequence("abc", "ABC") == ""
    assert longest_common_subsequence("aBc", "abc") == "ac"


def test_agrees_with_brute_force_on_every_short_pair() -> None:
    """Returns a common subsequence of the greatest length for every short pair.

    Every pair of strings of up to five characters over "ab", and up to four
    over "abc".
    """
    for alphabet, longest in (("ab", 5), ("abc", 4)):
        words = [
            "".join(letters)
            for size in range(longest + 1)
            for letters in product(alphabet, repeat=size)
        ]
        for first in words:
            for second in words:
                check(first, second, best_length(first, second))


def test_handles_strings_of_five_hundred_characters() -> None:
    """Fills and walks back through a 500 x 500 table within the time limit.

    "ab" repeated against "ba" repeated: dropping the first character of one
    and the last of the other leaves them equal, and nothing longer is shared.
    """
    check("ab" * 250, "ba" * 250, 499)
    assert longest_common_subsequence("a" * 500, "b" * 250 + "a" * 250) == "a" * 250
