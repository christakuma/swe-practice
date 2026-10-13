"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import WordStore

VOCABULARY = ("", "a", "b", "ab", "ba", "aa", "abb")


def matches(pattern: str, word: str) -> bool:
    return len(pattern) == len(word) and all(
        p in (".", w) for p, w in zip(pattern, word, strict=True)
    )


def store_of(words: tuple[str, ...]) -> WordStore:
    store = WordStore()
    for word in words:
        store.add(word)
    return store


def test_counts_every_match() -> None:
    """Counts all three words that match a wildcard pattern."""
    assert store_of(("bad", "dad", "mad")).count(".ad") == 3


def test_counts_a_word_added_twice_once() -> None:
    """Does not count a repeated word twice."""
    store = store_of(("bad", "bed", "bad"))

    assert store.count("b.d") == 2
    assert store.count("bad") == 1


def test_matches_only_words_of_the_same_length() -> None:
    """Does not let a wildcard match zero or several characters."""
    store = store_of(("bad", "ba", "badly"))

    assert store.count("b.") == 1
    assert store.count("b..") == 1
    assert store.count("....") == 0


def test_counts_nothing_in_an_empty_store() -> None:
    """Returns 0 for any pattern when nothing is stored."""
    assert WordStore().count("...") == 0
    assert WordStore().count("") == 0


def test_counts_the_empty_word() -> None:
    """Counts the empty pattern only when the empty word was added."""
    assert store_of(("",)).count("") == 1
    assert store_of(("a",)).count("") == 0


def test_returns_an_int() -> None:
    """Returns an int rather than a bool."""
    assert type(store_of(("a",)).count("a")) is int
    assert type(store_of(("a",)).count("b")) is int


def test_agrees_with_checking_every_word() -> None:
    """Matches a check of every stored word, for every small store and pattern."""
    patterns = [
        "".join(letters) for size in range(4) for letters in product("ab.", repeat=size)
    ]
    for size in range(4):
        for words in combinations(VOCABULARY, size):
            store = store_of(words)
            for pattern in patterns:
                expected = sum(matches(pattern, word) for word in words)
                assert store.count(pattern) == expected, (words, pattern)


def test_handles_a_large_store() -> None:
    """Counts across a hundred thousand words within the time limit."""
    store = WordStore()
    for index in range(100_000):
        store.add(f"{index:05d}")

    assert store.count(".....") == 100_000
    assert store.count("12...") == 1000
    for index in range(20_000):
        assert store.count(f"{index:05d}") == 1
