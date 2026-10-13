"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_repeating_substring


def by_checking_every_substring(text: str, k: int) -> int:
    """The answer by counting inside every substring. An oracle."""
    best = 0
    for start in range(len(text)):
        counts: dict[str, int] = {}
        for end in range(start, len(text)):
            counts[text[end]] = counts.get(text[end], 0) + 1
            if end - start + 1 > best and min(counts.values()) >= k:
                best = end - start + 1
    return best


def nested(depth: int) -> str:
    """A string whose pieces nest `depth` levels deep when k is 2.

    It starts as "aa". Each level appends a new character and then the
    previous level's new character, so that one is no longer rare in the
    whole but is still rare inside the piece the new wall cuts off.
    """
    text = "aa"
    previous = ""
    for level in range(depth):
        fresh = chr(0x4E00 + level)
        text += fresh + previous
        previous = fresh
    return text


def test_finds_a_run_of_one_character() -> None:
    """Returns the run when the other characters fall short."""
    assert longest_repeating_substring("aaabb", 3) == 3


def test_finds_a_mixed_substring() -> None:
    """Returns a substring of several characters that each appear often enough."""
    assert longest_repeating_substring("ababbc", 2) == 5


def test_returns_the_whole_string_when_it_qualifies() -> None:
    """Returns the full length when every character reaches k."""
    assert longest_repeating_substring("aabbcc", 2) == 6
    assert longest_repeating_substring("abcabcabc", 3) == 9


def test_returns_zero_when_nothing_qualifies() -> None:
    """Returns zero when no character appears k times anywhere."""
    assert longest_repeating_substring("abcde", 2) == 0
    assert longest_repeating_substring("aabb", 3) == 0


def test_handles_an_empty_string() -> None:
    """Returns zero for an empty string."""
    assert longest_repeating_substring("", 1) == 0
    assert longest_repeating_substring("", 3) == 0


def test_k_of_one_accepts_everything() -> None:
    """Returns the whole length when a single appearance is enough."""
    assert longest_repeating_substring("abcde", 1) == 5
    assert longest_repeating_substring("x", 1) == 1


def test_counts_inside_the_substring_not_in_the_whole_string() -> None:
    """Cuts a piece again when a character common overall is rare inside it.

    There are two b's in the string and one in each half. Splitting on the c
    alone and taking the longer half answers 3.
    """
    assert longest_repeating_substring("aabcbaa", 2) == 2
    assert longest_repeating_substring("bbaaacbd", 3) == 3


def test_the_answer_may_be_in_any_piece() -> None:
    """Finds the longest qualifying piece wherever it lies."""
    assert longest_repeating_substring("aaxbbbbycc", 2) == 4
    assert longest_repeating_substring("bbbbxaa", 2) == 4
    assert longest_repeating_substring("aaxbbbb", 2) == 4


def test_at_least_k_means_k_is_enough() -> None:
    """Accepts a character that appears exactly k times."""
    assert longest_repeating_substring("aabbb", 2) == 5
    assert longest_repeating_substring("aaa", 3) == 3
    assert longest_repeating_substring("aaa", 4) == 0


def test_the_substring_is_contiguous() -> None:
    """Does not gather a character's copies from either side of a wall."""
    assert longest_repeating_substring("axaxa", 3) == 0
    assert longest_repeating_substring("aaxaa", 4) == 0


def test_agrees_with_checking_every_substring() -> None:
    """Matches a count inside every substring, for every short string and k.

    Every string of up to eight characters over a, b and c, with k from one
    to four.
    """
    for size in range(9):
        for letters in product("abc", repeat=size):
            text = "".join(letters)
            for k in range(1, 5):
                expected = by_checking_every_substring(text, k)

                assert longest_repeating_substring(text, k) == expected, (text, k)


def test_a_shallow_nest_agrees_with_checking_every_substring() -> None:
    """Matches the same check on strings whose pieces nest inside each other."""
    for depth in range(12):
        text = nested(depth)

        assert longest_repeating_substring(text, 2) == by_checking_every_substring(
            text, 2
        ), depth


def test_handles_pieces_nested_deeper_than_python_will_recurse() -> None:
    """Works through fifteen hundred levels of nesting.

    Each level's wall cuts off a piece that needs cutting again, fifteen
    hundred times over, before reaching the "aa" at the bottom. One function
    call per level is more than Python allows.
    """
    assert longest_repeating_substring(nested(1_500), 2) == 2


def test_handles_a_long_string() -> None:
    """Searches ten thousand characters.

    Five thousand characters of "abab...", a c, 4,998 more of the same and
    a d. The c and d are walls for any k above one. The longer piece holds
    2,500 of each letter, which is exactly enough for k of 2,500 and one
    short for 2,501 -- and the whole string's 4,999 of each does not help,
    because the count that matters is the one inside the piece.
    """
    text = "ab" * 2_500 + "c" + "ab" * 2_499 + "d"

    assert longest_repeating_substring(text, 1) == 10_000
    assert longest_repeating_substring(text, 2_500) == 5_000
    assert longest_repeating_substring(text, 2_501) == 0
