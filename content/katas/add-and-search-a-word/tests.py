"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import WordStore


def model(words: set[str], pattern: str) -> bool:
    """Match the pattern against a plain set of words -- an independent oracle.

    O(total characters) per search, which is exactly what the trie exists to
    avoid, so it shares none of its structure or pruning.
    """
    return any(
        len(word) == len(pattern)
        and all(p in (".", w) for p, w in zip(pattern, word, strict=True))
        for word in words
    )


def store_of(*words: str) -> WordStore:
    """A store holding `words`."""
    store = WordStore()
    for word in words:
        store.add(word)
    return store


def test_handles_the_worked_examples() -> None:
    """Returns the documented answers."""
    store = store_of("bad", "dad", "mad")

    assert store.search("pad") is False
    assert store.search("bad") is True
    assert store.search(".ad") is True
    assert store.search("b..") is True
    assert store.search("...") is True


def test_requires_the_lengths_to_match() -> None:
    """Does not let a wildcard match zero or several characters.

    "b." is two characters and every stored word is three, so nothing matches.
    A solution treating "." as "anything from here" reports True.
    """
    store = store_of("bad", "dad", "mad")

    assert store.search("b.") is False
    assert store.search("b...") is False
    assert store.search(".") is False
    assert store.search("ba") is False


def test_handles_an_empty_store() -> None:
    """Returns False for any pattern when nothing is stored."""
    store = WordStore()

    assert store.search("") is False
    assert store.search(".") is False
    assert store.search("a") is False
    assert store.search("...") is False


def test_handles_the_empty_word() -> None:
    """Matches the empty pattern only when the empty word was added."""
    store = store_of("")

    assert store.search("") is True
    assert store.search(".") is False
    assert store_of("a").search("") is False


def test_matches_an_all_wildcard_pattern() -> None:
    """Matches any stored word of the right length."""
    store = store_of("a", "bb", "ccc")

    assert store.search(".") is True
    assert store.search("..") is True
    assert store.search("...") is True
    assert store.search("....") is False


def test_matches_a_wildcard_in_every_position() -> None:
    """Handles a wildcard at the start, middle and end."""
    store = store_of("abc")

    assert store.search(".bc") is True
    assert store.search("a.c") is True
    assert store.search("ab.") is True
    assert store.search("..c") is True
    assert store.search("a..") is True
    assert store.search(".b.") is True
    assert store.search(".bd") is False


def test_keeps_searching_after_a_failed_branch() -> None:
    """Tries every child at a wildcard, not just the first.

    The wildcard must branch across all children. Whichever "bad" or "cat" is
    tried first fails for one of these patterns, so a solution that commits to
    one child returns False.
    """
    store = store_of("bad", "cat")

    assert store.search(".ad") is True
    assert store.search(".at") is True
    assert store.search(".ax") is False


def test_does_not_match_a_prefix() -> None:
    """Requires the whole word, not a prefix of one."""
    store = store_of("apple")

    assert store.search("app") is False
    assert store.search("app..") is True
    assert store.search("apple") is True


def test_handles_words_that_prefix_each_other() -> None:
    """Keeps both when one stored word is a prefix of another."""
    store = store_of("a", "ab", "abc")

    assert store.search("a") is True
    assert store.search(".") is True
    assert store.search("..") is True
    assert store.search("...") is True
    assert store.search("....") is False


def test_handles_repeated_addition() -> None:
    """Changes nothing when the same word is added twice."""
    store = store_of("bad", "bad")

    assert store.search("bad") is True
    assert store.search("ba") is False


def test_handles_non_letter_characters() -> None:
    """Stores and matches characters outside the lowercase alphabet."""
    store = store_of("a-b", "é!", "日本")

    assert store.search("a-b") is True
    assert store.search("a.b") is True
    assert store.search("é!") is True
    assert store.search("..") is True
    assert store.search("日.") is True


def test_returns_bools() -> None:
    """Returns True or False rather than truthy values."""
    store = store_of("a")

    assert store.search("a") is True
    assert store.search("b") is False


def test_agrees_with_a_set_model_across_every_small_vocabulary() -> None:
    """Matches a set-of-words model for every small vocabulary and pattern.

    Every subset of the strings over {a, b} up to length two, crossed with
    every pattern over {a, b, .} up to length three. The length rule and the
    wildcard branching each fail only for particular combinations.
    """
    vocabulary = [
        "".join(characters)
        for length in range(3)
        for characters in product("ab", repeat=length)
    ]
    patterns = [
        "".join(characters)
        for length in range(4)
        for characters in product("ab.", repeat=length)
    ]
    for mask in range(1 << len(vocabulary)):
        words = {vocabulary[i] for i in range(len(vocabulary)) if mask >> i & 1}
        store = store_of(*words)
        for pattern in patterns:
            assert store.search(pattern) is model(words, pattern), (words, pattern)


def test_prunes_on_literal_characters() -> None:
    """Answers literal-prefixed patterns without searching the whole store.

    A hundred thousand words spread over many first characters. A literal
    first character should confine the search to one subtree; a solution that
    matches against every stored word is O(total characters) per query and
    does not finish a thousand of them.
    """
    store = WordStore()
    for value in range(100_000):
        store.add(f"{chr(97 + value % 26)}{value:06d}")

    for _ in range(1_000):
        assert store.search("a000000") is True
        assert store.search("a999999") is False
        assert store.search("a00000.") is True
        assert store.search("z000025") is True
