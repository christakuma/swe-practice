"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import fewest_words


def by_trying_every_split(text: str, words: list[str]) -> int:
    """Try every dictionary word at the front, recursively."""
    if not text:
        return 0
    best = -1
    for word in set(words):
        if text.startswith(word):
            rest = by_trying_every_split(text[len(word) :], words)
            if rest >= 0 and (best < 0 or rest + 1 < best):
                best = rest + 1
    return best


def test_counts_the_words_in_the_only_split() -> None:
    """Returns the number of words when the string splits one way."""
    assert fewest_words("applepenapple", ["apple", "pen"]) == 3
    assert fewest_words("leetcode", ["leet", "code"]) == 2


def test_a_dictionary_word_is_one_word() -> None:
    """Returns 1 when the whole string is in the dictionary."""
    assert fewest_words("apple", ["apple", "app", "le"]) == 1


def test_prefers_fewer_longer_words() -> None:
    """Chooses the split with the fewest words among several."""
    assert fewest_words("aaaa", ["a", "aa", "aaa"]) == 2
    assert fewest_words("aaaaaa", ["a", "aaa"]) == 2
    assert fewest_words("abab", ["a", "b", "ab", "abab"]) == 1


def test_returns_minus_one_when_it_cannot_be_split() -> None:
    """Returns -1 when no sequence of words spells the string."""
    assert fewest_words("catsandog", ["cats", "dog", "sand", "and", "cat"]) == -1
    assert fewest_words("abc", ["ab", "bc"]) == -1
    assert fewest_words("a", []) == -1


def test_the_empty_string_needs_no_words() -> None:
    """Returns 0 for the empty string, with or without a dictionary."""
    assert fewest_words("", ["a"]) == 0
    assert fewest_words("", []) == 0


def test_the_longest_word_first_is_not_always_fewest() -> None:
    """Passes over the longest word at the front when a shorter one leads to fewer.

    "abcd" then "e", "f", "g" is four words. "abc" then "defg" is two.
    """
    assert fewest_words("abcdefg", ["abcd", "abc", "defg", "e", "f", "g"]) == 2


def test_the_longest_word_first_can_miss_the_only_split() -> None:
    """Finds a split that starts with the shorter word when the longer is a dead end."""
    assert fewest_words("abcd", ["abc", "ab", "cd"]) == 2
    assert fewest_words("aaab", ["aaa", "aa", "ab"]) == 2


def test_a_longer_last_word_is_not_always_better() -> None:
    """Compares every word the string could end with, not just the last one tried.

    "xyab" can end with "b" after "xya", which is two words, or with "ab"
    after "x" and "y", which is three.
    """
    assert fewest_words("xyab", ["xya", "b", "ab", "x", "y"]) == 2
    assert fewest_words("xyab", ["x", "y", "ab", "b", "xya"]) == 2


def test_an_unsplittable_middle_does_not_look_splittable() -> None:
    """Does not build on a prefix that cannot itself be spelled.

    "xb" ends with the word "b", but nothing spells the "x" before it.
    """
    assert fewest_words("xb", ["b"]) == -1
    assert fewest_words("abxcd", ["ab", "cd", "abx"]) == 2
    assert fewest_words("abxcd", ["ab", "cd"]) == -1


def test_words_may_be_reused_and_repeated_in_the_dictionary() -> None:
    """Uses one word many times, and tolerates duplicates in the dictionary."""
    assert fewest_words("ababab", ["ab"]) == 3
    assert fewest_words("ababab", ["ab", "ab", "abab"]) == 2


def test_agrees_with_trying_every_split() -> None:
    """Matches an exhaustive search for every short string and small dictionary.

    Every string of up to six characters over "ab", against every dictionary
    of one to three of the words a, b, aa, ab, ba, aab, bab.
    """
    vocabulary = ["a", "b", "aa", "ab", "ba", "aab", "bab"]
    dictionaries = [
        list(chosen) for size in (1, 2, 3) for chosen in combinations(vocabulary, size)
    ]
    for size in range(7):
        for characters in product("ab", repeat=size):
            text = "".join(characters)
            for words in dictionaries:
                expected = by_trying_every_split(text, words)
                assert fewest_words(text, words) == expected, (text, words)


def test_leaves_the_dictionary_alone() -> None:
    """Does not modify the list of words."""
    words = ["b", "a"]

    fewest_words("ab", words)

    assert words == ["b", "a"]


def test_handles_a_long_string() -> None:
    """Handles a thousand characters, which have far too many splits to list.

    A thousand a's and words of one to twenty a's: the fewest is fifty words
    of twenty. With a b at the end and no word containing one, there is no
    split at all.
    """
    words = ["a" * size for size in range(1, 21)]

    assert fewest_words("a" * 1000, words) == 50
    assert fewest_words("a" * 999, words) == 50
    assert fewest_words("a" * 999 + "b", words) == -1
