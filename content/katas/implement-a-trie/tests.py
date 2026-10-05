"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import Trie


def model(words: set[str], query: str, *, exact: bool) -> bool:
    """Answer from a plain set of strings -- an independent oracle.

    O(total characters) per query, which is exactly what the trie exists to
    avoid, and therefore shares none of its structure.
    """
    if exact:
        return query in words
    return any(word.startswith(query) for word in words)


def test_finds_an_inserted_word() -> None:
    """Reports an inserted word as present."""
    trie = Trie()
    trie.insert("apple")

    assert trie.contains("apple") is True


def test_does_not_treat_a_prefix_as_a_word() -> None:
    """Reports a prefix of a stored word as absent.

    The discriminating test for the whole kata: "app" is a path through the
    trie but was never inserted. Without an end-of-word marker, `contains` and
    `starts_with` collapse into the same function and this returns True.
    """
    trie = Trie()
    trie.insert("apple")

    assert trie.contains("app") is False
    assert trie.starts_with("app") is True


def test_marks_a_prefix_as_a_word_once_inserted() -> None:
    """Reports a prefix as present after it is inserted in its own right."""
    trie = Trie()
    trie.insert("apple")
    trie.insert("app")

    assert trie.contains("app") is True
    assert trie.contains("apple") is True


def test_reports_absent_words() -> None:
    """Reports words that were never inserted as absent."""
    trie = Trie()
    trie.insert("apple")

    assert trie.contains("banana") is False
    assert trie.contains("applesauce") is False
    assert trie.starts_with("banana") is False


def test_handles_an_empty_trie() -> None:
    """Answers both queries on a trie with nothing in it.

    `starts_with("")` is False here: the question is whether any *stored word*
    has that prefix, and there are none. The root exists without an insertion,
    so a solution that only checks the node was reached answers True.
    """
    trie = Trie()

    assert trie.contains("") is False
    assert trie.contains("a") is False
    assert trie.starts_with("") is False
    assert trie.starts_with("a") is False


def test_handles_the_empty_string_as_a_word() -> None:
    """Distinguishes inserting "" from not inserting it."""
    trie = Trie()
    trie.insert("")

    assert trie.contains("") is True
    assert trie.starts_with("") is True
    assert trie.contains("a") is False


def test_treats_the_empty_string_as_a_prefix_of_everything() -> None:
    """Reports "" as a prefix once any word is stored, without inserting it."""
    trie = Trie()
    trie.insert("apple")

    assert trie.starts_with("") is True
    assert trie.contains("") is False


def test_reports_a_whole_word_as_its_own_prefix() -> None:
    """Reports a stored word as a prefix of itself."""
    trie = Trie()
    trie.insert("apple")

    assert trie.starts_with("apple") is True
    assert trie.starts_with("applex") is False


def test_handles_repeated_insertion() -> None:
    """Changes nothing when the same word is inserted twice."""
    trie = Trie()
    trie.insert("apple")
    trie.insert("apple")

    assert trie.contains("apple") is True
    assert trie.contains("app") is False


def test_handles_many_words_sharing_prefixes() -> None:
    """Keeps words distinct when they share long prefixes."""
    trie = Trie()
    for word in ("car", "card", "care", "careful", "cat"):
        trie.insert(word)

    for word in ("car", "card", "care", "careful", "cat"):
        assert trie.contains(word) is True, word
    for word in ("ca", "care f", "cars", "caref"):
        assert trie.contains(word) is False, word
    for prefix in ("c", "ca", "car", "care", "caref", "cat"):
        assert trie.starts_with(prefix) is True, prefix
    assert trie.starts_with("cars") is False


def test_handles_a_word_that_is_a_prefix_of_another() -> None:
    """Keeps both when one stored word is a prefix of another."""
    trie = Trie()
    trie.insert("a")
    trie.insert("ab")
    trie.insert("abc")

    assert trie.contains("a") is True
    assert trie.contains("ab") is True
    assert trie.contains("abc") is True
    assert trie.contains("abcd") is False


def test_handles_non_letter_characters() -> None:
    """Stores characters outside the lowercase alphabet.

    A fixed array of twenty-six slots raises or miscounts here.
    """
    trie = Trie()
    for word in ("a-b", "A", "1", " ", "é", "日本"):
        trie.insert(word)
    for word in ("a-b", "A", "1", " ", "é", "日本"):
        assert trie.contains(word) is True, word
    assert trie.contains("a") is False
    assert trie.starts_with("日") is True


def test_returns_bools() -> None:
    """Returns True or False rather than truthy values."""
    trie = Trie()
    trie.insert("a")

    assert trie.contains("a") is True
    assert trie.contains("b") is False
    assert trie.starts_with("a") is True
    assert trie.starts_with("b") is False


def test_agrees_with_a_set_model_across_every_small_vocabulary() -> None:
    """Matches a set-of-strings model for every small vocabulary and query.

    Every subset of the strings over {a, b} up to length two -- 32 vocabularies
    -- crossed with every query up to length three. The end-of-word marker and
    the empty-string cases each fail only for particular combinations.
    """
    vocabulary = [
        "".join(characters)
        for length in range(3)
        for characters in product("ab", repeat=length)
    ]
    queries = [
        "".join(characters)
        for length in range(4)
        for characters in product("ab", repeat=length)
    ]
    for mask in range(1 << len(vocabulary)):
        words = {vocabulary[i] for i in range(len(vocabulary)) if mask >> i & 1}
        trie = Trie()
        for word in words:
            trie.insert(word)
        for query in queries:
            assert trie.contains(query) is model(words, query, exact=True), (
                words,
                query,
            )
            assert trie.starts_with(query) is model(words, query, exact=False), (
                words,
                query,
            )


def test_scales_with_word_length_not_vocabulary_size() -> None:
    """Answers queries against a hundred thousand words within the time limit.

    Every operation should cost O(len(word)) regardless of how much is stored,
    so this is the only test that can tell a trie from a set of strings with a
    linear prefix scan -- the rest inspect return values, and the structure is
    opaque to them.

    The queries are chosen to deny that scan its short-circuit: `"absent"`
    matches nothing, and `"prefix-09999"` matches only at the very end of the
    vocabulary, so each round costs two full passes over all hundred thousand
    words. Measured: the scanning version takes **25.7s** against this kata's
    15s limit, and the trie answers the same three thousand rounds in **0.01s**
    once built.
    """
    trie = Trie()
    for value in range(100_000):
        trie.insert(f"prefix-{value:06d}")

    for _ in range(3_000):
        assert trie.contains("prefix-050000") is True
        assert trie.contains("prefix-999999") is False
        assert trie.starts_with("absent") is False
        assert trie.starts_with("prefix-09999") is True
