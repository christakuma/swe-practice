"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise, product

from solution import is_sorted

ENGLISH = "abcdefghijklmnopqrstuvwxyz"


def in_order(first: str, second: str, alphabet: str) -> bool:
    """Compare two words a character at a time."""
    for a, b in zip(first, second, strict=False):
        if a != b:
            return alphabet.index(a) < alphabet.index(b)
    return len(first) <= len(second)


def test_uses_the_given_alphabet() -> None:
    """Accepts words sorted by an unfamiliar alphabet."""
    assert is_sorted(["hello", "leetcode"], "hlabcdefgijkmnopqrstuvwxyz") is True


def test_rejects_words_out_of_order() -> None:
    """Rejects a pair that the alphabet puts the other way round."""
    assert is_sorted(["word", "world", "row"], "worldabcefghijkmnpqstuvxyz") is False


def test_does_not_use_ordinary_order() -> None:
    """Rejects ordinary alphabetical order under a reversed alphabet."""
    assert is_sorted(["a", "b"], ENGLISH[::-1]) is False
    assert is_sorted(["b", "a"], ENGLISH[::-1]) is True


def test_a_prefix_comes_first() -> None:
    """Puts a word before a longer word it is a prefix of, and not after."""
    assert is_sorted(["app", "apple"], ENGLISH) is True
    assert is_sorted(["apple", "app"], ENGLISH) is False
    assert is_sorted(["", "a"], ENGLISH) is True
    assert is_sorted(["a", ""], ENGLISH) is False


def test_handles_short_lists_and_repeats() -> None:
    """Accepts no words, one word, and equal neighbours."""
    assert is_sorted([], ENGLISH) is True
    assert is_sorted(["solo"], ENGLISH) is True
    assert is_sorted(["same", "same"], ENGLISH) is True


def test_checks_every_pair_of_neighbours() -> None:
    """Rejects a list whose only fault is at the end."""
    assert is_sorted(["a", "b", "c", "b"], ENGLISH) is False


def test_agrees_with_comparing_neighbours_by_hand() -> None:
    """Matches a character-by-character check for every short list."""
    pool = [
        "".join(letters) for size in range(3) for letters in product("ab", repeat=size)
    ]
    for alphabet in ("ab", "ba"):
        for size in range(4):
            for chosen in product(pool, repeat=size):
                words = list(chosen)
                expected = all(
                    in_order(first, second, alphabet)
                    for first, second in pairwise(words)
                )
                assert is_sorted(words, alphabet) is expected, (words, alphabet)


def test_checks_a_hundred_thousand_words() -> None:
    """Checks a hundred thousand words within the time limit."""
    words = [f"{index:05d}" for index in range(100_000)]

    assert is_sorted(words, "0123456789") is True
    assert is_sorted(words, "9876543210") is False
