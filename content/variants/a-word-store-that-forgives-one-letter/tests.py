"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import WordStore


def store_of(*words: str) -> WordStore:
    store = WordStore()
    for word in words:
        store.add(word)
    return store


def one_away(stored: tuple[str, ...], word: str) -> bool:
    """Whether some stored word of the same length differs in one position."""
    return any(
        len(other) == len(word)
        and sum(a != b for a, b in zip(other, word, strict=True)) == 1
        for other in stored
    )


def test_matches_a_word_one_letter_away() -> None:
    """Finds a stored word that differs in one position, wherever it is."""
    store = store_of("hello")

    assert store.search("jello")
    assert store.search("hallo")
    assert store.search("hellp")


def test_does_not_match_the_word_itself() -> None:
    """Does not count a stored word as a match for itself."""
    store = store_of("hello", "leetcode")

    assert not store.search("hello")
    assert not store.search("leetcode")


def test_matches_a_stored_word_through_its_neighbour() -> None:
    """Finds a stored word once another word one letter away is stored too."""
    store = store_of("hello", "hallo")

    assert store.search("hello")
    assert store.search("hallo")


def test_does_not_match_two_letters_away() -> None:
    """Rejects a word that differs in two positions."""
    store = store_of("hello")

    assert not store.search("hxllx")
    assert not store.search("jellp")


def test_only_matches_words_of_the_same_length() -> None:
    """Rejects words that are longer or shorter than every stored word."""
    store = store_of("cat")

    assert not store.search("ca")
    assert not store.search("cart")
    assert not store.search("at")
    assert store.search("bat")


def test_a_dot_is_an_ordinary_character() -> None:
    """Treats a dot as one more character, in a search and in a stored word."""
    store = store_of("a.c")

    assert not store.search("a.c")
    assert store.search("abc")
    assert not store.search("xbc")
    assert not store_of("abc", "xyz").search("...")


def test_the_empty_word_never_matches() -> None:
    """Returns False for the empty word, which has no position to differ in."""
    assert not WordStore().search("")
    assert not store_of("").search("")
    assert not store_of("").search("a")


def test_adding_a_word_twice_changes_nothing() -> None:
    """Does not let a word added twice match itself."""
    store = store_of("abc", "abc")

    assert not store.search("abc")
    assert store.search("abd")


def test_agrees_with_comparing_every_stored_word() -> None:
    """Matches a word-by-word comparison for every small store and search.

    Every pair of words up to three characters over "ab." as the store, and
    every such word as the search.
    """
    words = ["".join(letters) for n in range(4) for letters in product("ab.", repeat=n)]
    for stored in combinations(words, 2):
        store = store_of(*stored)
        for word in words:
            assert store.search(word) == one_away(stored, word), (stored, word)


def test_searches_a_large_store() -> None:
    """Answers 2,000 searches of 2,000 stored eight-letter words correctly.

    Each search is a stored word with its first letter changed, so every one
    of them is a match unless the changed word happens to be stored too.
    """
    letters = "abcde"
    words = []
    seed = 7
    for _ in range(2000):
        word = []
        for _ in range(8):
            seed = (seed * 1103515245 + 12345) % 2**31
            word.append(letters[(seed >> 16) % 5])
        words.append("".join(word))
    stored = set(words)
    store = store_of(*words)

    found = 0
    for word in words:
        probe = ("b" if word[0] == "a" else "a") + word[1:]
        hit = store.search(probe)
        if probe not in stored:
            assert hit, probe
        found += hit
    assert found >= 1500
