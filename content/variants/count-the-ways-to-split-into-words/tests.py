"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import count_segmentations

POOL = ["a", "b", "ab", "ba", "aa", "aab"]


def by_recursion(text: str, words: frozenset[str]) -> int:
    """Try every word as the first one and recurse on what is left."""
    if not text:
        return 1
    return sum(
        by_recursion(text[len(word) :], words)
        for word in words
        if text.startswith(word)
    )


def test_counts_the_documented_splits() -> None:
    """Counts both ways to split the worked example."""
    words = ["cat", "cats", "and", "sand", "dog"]

    assert count_segmentations("catsanddog", words) == 2


def test_counts_every_arrangement_of_reused_words() -> None:
    """Counts splits that reuse a word, in every arrangement."""
    assert count_segmentations("aaa", ["a", "aa"]) == 3


def test_returns_zero_when_the_string_cannot_be_split() -> None:
    """Returns 0 when no sequence of words covers the string."""
    assert count_segmentations("catsandog", ["cats", "dog", "sand", "and", "cat"]) == 0
    assert count_segmentations("a", []) == 0


def test_counts_one_way_to_split_nothing() -> None:
    """Counts one way to split the empty string, with or without words."""
    assert count_segmentations("", ["a"]) == 1
    assert count_segmentations("", []) == 1


def test_ignores_a_repeated_word() -> None:
    """Does not count a split twice because its word is listed twice."""
    assert count_segmentations("aa", ["a", "a"]) == 1


def test_agrees_with_trying_every_first_word() -> None:
    """Matches a recursive count for every short string and small dictionary."""
    for size in range(1, 4):
        for chosen in combinations(POOL, size):
            for length in range(8):
                for letters in product("ab", repeat=length):
                    text = "".join(letters)
                    expected = by_recursion(text, frozenset(chosen))
                    assert count_segmentations(text, list(chosen)) == expected, (
                        text,
                        chosen,
                    )


def test_counts_an_enormous_number_exactly() -> None:
    """Counts the splits of a thousand characters exactly.

    With words of one, two and three a's the count for each length is the sum
    of the previous three, which is checked here by a plain loop. The answer
    has over two hundred and sixty digits.
    """
    before, last, current = 0, 0, 1
    for _ in range(1000):
        before, last, current = last, current, before + last + current

    assert count_segmentations("a" * 1000, ["a", "aa", "aaa"]) == current
