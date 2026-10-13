"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import smallest_window


def by_starting_everywhere(text: str, pattern: str) -> str:
    """The answer by matching forward from every position. An oracle.

    From each start it takes each pattern character at the first place it
    can, which gives the shortest window with that start. No backward walk.
    """
    if not pattern:
        return ""
    best = ""
    for start in range(len(text)):
        matched = 0
        for end in range(start, len(text)):
            if text[end] == pattern[matched]:
                matched += 1
                if matched == len(pattern):
                    if not best or end - start + 1 < len(best):
                        best = text[start : end + 1]
                    break
    return best


def test_finds_the_pattern_spread_through_a_window() -> None:
    """Returns the shortest substring holding the pattern in order."""
    assert smallest_window("abcdebdde", "bde") == "bcde"


def test_order_matters() -> None:
    """Returns nothing when the characters are present but out of order.

    A window that only counts characters accepts both of these.
    """
    assert smallest_window("cab", "abc") == ""
    assert smallest_window("ba", "ab") == ""


def test_skips_a_window_whose_characters_are_out_of_order() -> None:
    """Passes over a short stretch with the right characters in the wrong order."""
    assert smallest_window("bca-a-b-c", "abc") == "a-b-c"
    assert smallest_window("ba__ab", "ab") == "ab"


def test_handles_empty_inputs() -> None:
    """Returns the empty string for an empty text or an empty pattern."""
    assert smallest_window("", "a") == ""
    assert smallest_window("abc", "") == ""
    assert smallest_window("", "") == ""


def test_returns_nothing_when_the_pattern_is_not_there() -> None:
    """Returns the empty string when a character is missing or there are too few."""
    assert smallest_window("abc", "abd") == ""
    assert smallest_window("aab", "aaa") == ""
    assert smallest_window("ab", "abc") == ""


def test_the_pattern_itself_is_the_tightest_window() -> None:
    """Returns the pattern when it appears with nothing in between."""
    assert smallest_window("xxabcxx", "abc") == "abc"
    assert smallest_window("abc", "abc") == "abc"


def test_tightens_the_start_of_a_window() -> None:
    """Starts the window at the last usable first character, not the first one seen."""
    assert smallest_window("aaab", "ab") == "ab"
    assert smallest_window("abab-b", "ab") == "ab"
    assert smallest_window("a-ab-b", "ab") == "ab"


def test_a_later_window_can_be_shorter() -> None:
    """Keeps looking after the first window and returns a shorter later one."""
    assert smallest_window("axxbab", "ab") == "ab"
    assert smallest_window("a---b--a-b", "ab") == "a-b"


def test_the_next_window_may_begin_inside_the_last_one() -> None:
    """Finds a window that starts before the previous window ends.

    The first window is "axa". The best one, "aa", begins on its final
    character -- so the search has to resume from inside it.
    """
    assert smallest_window("axaa", "aa") == "aa"
    assert smallest_window("abxabb", "abb") == "abb"


def test_returns_the_earliest_of_equally_short_windows() -> None:
    """Prefers the window that starts first when two are the same length."""
    assert smallest_window("a-b_a+b", "ab") == "a-b"
    assert smallest_window("xaybxazb", "ab") == "ayb"


def test_a_repeated_pattern_character_needs_that_many() -> None:
    """Requires each occurrence in the pattern to be matched by its own character."""
    assert smallest_window("abcabca", "aa") == "abca"
    assert smallest_window("banana", "nn") == "nan"
    assert smallest_window("banana", "aaa") == "anana"


def test_a_single_character_pattern() -> None:
    """Returns the character itself for a pattern of one."""
    assert smallest_window("hello", "l") == "l"
    assert smallest_window("hello", "z") == ""


def test_case_matters() -> None:
    """Does not match an upper-case character with its lower-case form."""
    assert smallest_window("aAbB", "ab") == "aAb"
    assert smallest_window("AB", "ab") == ""


def test_agrees_with_starting_everywhere_over_two_letters() -> None:
    """Matches a search from every position for every text up to nine letters.

    Every text of up to nine characters over a and b, against every pattern
    of up to four.
    """
    patterns = [
        "".join(letters)
        for size in range(1, 5)
        for letters in product("ab", repeat=size)
    ]
    for size in range(10):
        for letters in product("ab", repeat=size):
            text = "".join(letters)
            for pattern in patterns:
                expected = by_starting_everywhere(text, pattern)

                assert smallest_window(text, pattern) == expected, (text, pattern)


def test_agrees_with_starting_everywhere_over_three_letters() -> None:
    """Matches the same search for every text up to six letters over a, b and c."""
    patterns = [
        "".join(letters)
        for size in range(1, 4)
        for letters in product("abc", repeat=size)
    ]
    for size in range(7):
        for letters in product("abc", repeat=size):
            text = "".join(letters)
            for pattern in patterns:
                expected = by_starting_everywhere(text, pattern)

                assert smallest_window(text, pattern) == expected, (text, pattern)


def test_handles_a_long_text_with_one_tight_window() -> None:
    """Searches twenty thousand characters for a window near the end.

    The text is "a-b-c-" over and over, in which the tightest window for
    "abc" is five long. One "abc" with nothing between is planted two
    thirds of the way through.
    """
    text = "a-b-c-" * 3_333
    planted = 13_332
    text = text[:planted] + "abc" + text[planted + 3 :]

    assert len(text) == 19_998
    assert smallest_window(text, "abc") == "abc"
    assert smallest_window(text.replace("abc", "a-b"), "abc") == "a-b-c"


def test_handles_a_long_pattern_in_a_long_text() -> None:
    """Matches a hundred-character pattern against twenty thousand characters.

    The text repeats "ab" and the pattern is fifty of them, so every window
    is exactly the pattern and the first one wins.
    """
    text = "ab" * 10_000
    pattern = "ab" * 50

    assert smallest_window(text, pattern) == pattern
    assert smallest_window(text, pattern + "c") == ""
