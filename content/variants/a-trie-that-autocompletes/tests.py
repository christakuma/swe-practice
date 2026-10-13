"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import Trie

WORDS = ["card", "car", "care", "cat", "dog", "do", "careful", "cart"]


def trie_of(*words: str) -> Trie:
    trie = Trie()
    for word in words:
        trie.insert(word)
    return trie


def by_filtering(words: tuple[str, ...], prefix: str, limit: int) -> list[str]:
    return sorted({word for word in words if word.startswith(prefix)})[:limit]


def test_lists_the_words_that_start_with_a_prefix() -> None:
    """Returns every match when there are fewer than the limit."""
    trie = trie_of(*WORDS)

    assert trie.complete("car", 10) == ["car", "card", "care", "careful", "cart"]
    assert trie.complete("d", 10) == ["do", "dog"]


def test_a_stored_word_completes_itself() -> None:
    """Includes the prefix when it is a stored word, and puts it first."""
    trie = trie_of(*WORDS)

    assert trie.complete("care", 10) == ["care", "careful"]
    assert trie.complete("dog", 10) == ["dog"]


def test_a_prefix_that_is_not_a_word_is_not_listed() -> None:
    """Leaves out the prefix itself when it was never inserted."""
    assert trie_of("card", "care").complete("car", 10) == ["card", "care"]


def test_stops_at_the_limit() -> None:
    """Returns the first matches in order when there are more than the limit."""
    trie = trie_of(*WORDS)

    assert trie.complete("ca", 3) == ["car", "card", "care"]
    assert trie.complete("ca", 1) == ["car"]
    assert trie.complete("", 2) == ["car", "card"]


def test_a_limit_of_zero_returns_nothing() -> None:
    """Returns an empty list for a limit of zero, even when the prefix is a word."""
    assert trie_of("a", "ab").complete("a", 0) == []


def test_returns_words_in_string_order_not_insertion_order() -> None:
    """Sorts the matches, whatever order they were inserted in."""
    trie = trie_of("bz", "ba", "bm", "b", "bab")

    assert trie.complete("b", 10) == ["b", "ba", "bab", "bm", "bz"]


def test_a_shorter_word_comes_before_its_extensions() -> None:
    """Lists a word before longer words that start with it, not by length overall."""
    trie = trie_of("abc", "b", "ab", "a")

    assert trie.complete("", 10) == ["a", "ab", "abc", "b"]
    assert trie.complete("", 3) == ["a", "ab", "abc"]


def test_returns_nothing_for_a_prefix_nothing_starts_with() -> None:
    """Returns an empty list when no stored word begins with the prefix."""
    trie = trie_of(*WORDS)

    assert trie.complete("x", 5) == []
    assert trie.complete("cards", 5) == []
    assert Trie().complete("", 5) == []


def test_the_empty_prefix_matches_everything() -> None:
    """Lists every word in order for the empty prefix."""
    assert trie_of(*WORDS).complete("", 10) == sorted(WORDS)


def test_the_empty_word_can_be_stored() -> None:
    """Lists the empty string first when it has been inserted."""
    trie = trie_of("b", "", "a")

    assert trie.complete("", 5) == ["", "a", "b"]
    assert trie.complete("", 1) == [""]


def test_inserting_twice_lists_once() -> None:
    """Lists a word once however many times it was inserted."""
    assert trie_of("go", "go", "gone", "go").complete("g", 5) == ["go", "gone"]


def test_orders_any_characters_as_python_does() -> None:
    """Orders upper case, digits and punctuation by ordinary string comparison."""
    words = ["a", "B", "1", "~", "A", "b", " "]

    assert trie_of(*words).complete("", 10) == sorted(words)


def test_does_not_hand_out_its_internals() -> None:
    """Returns a fresh list each time, so changing one does not affect the next."""
    trie = trie_of("x", "xy")
    first = trie.complete("x", 5)
    first.append("junk")

    assert trie.complete("x", 5) == ["x", "xy"]


def test_agrees_with_filtering_a_sorted_list() -> None:
    """Matches sort-and-filter for every small set of words.

    Every set of three words of up to three letters over "ab", against every
    prefix of up to three letters and every limit from 0 to 4.
    """
    vocabulary = [
        "".join(letters) for size in range(4) for letters in product("ab", repeat=size)
    ]
    for stored in combinations(vocabulary, 3):
        trie = trie_of(*stored)
        for prefix in vocabulary:
            for limit in range(5):
                expected = by_filtering(stored, prefix, limit)
                assert trie.complete(prefix, limit) == expected, (stored, prefix, limit)


def test_stops_early_among_many_matches() -> None:
    """Returns three suggestions from 50,000 matches, ten thousand times over.

    Every stored word begins with "p". Gathering all 50,000 for each call and
    then keeping three is five hundred million words handled; a walk that
    stops at three visits a dozen nodes.
    """
    letters = "abcdefghij"
    trie = Trie()
    for digits in product(letters, repeat=4):
        for ending in ("", "x", "xy", "z", "zz"):
            trie.insert("p" + "".join(digits) + ending)

    for _ in range(10_000):
        assert trie.complete("p", 3) == ["paaaa", "paaaax", "paaaaxy"]
    assert trie.complete("pjjjj", 9) == [
        "pjjjj",
        "pjjjjx",
        "pjjjjxy",
        "pjjjjz",
        "pjjjjzz",
    ]
