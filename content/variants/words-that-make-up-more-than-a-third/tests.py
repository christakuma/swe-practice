"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc
from collections import Counter
from itertools import product

from solution import heavy_hitters


def by_counting(words: list[str]) -> list[str]:
    return sorted(
        word for word, count in Counter(words).items() if 3 * count > len(words)
    )


def test_finds_a_single_frequent_word() -> None:
    """Returns the one word that appears more than a third of the time."""
    assert heavy_hitters(["a", "b", "a", "c", "a"]) == ["a"]
    assert heavy_hitters(["z"]) == ["z"]


def test_finds_two_frequent_words() -> None:
    """Returns both words when two clear the bar."""
    assert heavy_hitters(["x", "y", "y", "x", "z", "x", "y"]) == ["x", "y"]
    assert heavy_hitters(["p", "q"]) == ["p", "q"]


def test_returns_them_in_alphabetical_order() -> None:
    """Sorts the answer, whichever word was met first or is more frequent."""
    assert heavy_hitters(["b", "b", "a", "a"]) == ["a", "b"]
    assert heavy_hitters(["z", "a", "z", "a", "a"]) == ["a", "z"]


def test_exactly_a_third_is_not_enough() -> None:
    """Leaves out a word that appears exactly a third of the time."""
    assert heavy_hitters(["a", "b", "c"]) == []
    assert heavy_hitters(["a", "a", "b", "b", "c", "c"]) == []
    assert heavy_hitters(["a", "a", "b", "c", "d", "e"]) == []


def test_returns_nothing_when_no_word_is_frequent() -> None:
    """Returns an empty list when every word is rare, although candidates survive.

    The candidate scan always ends holding something. Without a second count
    these lists report words that appear once.
    """
    assert heavy_hitters(["a", "b", "c", "d"]) == []
    assert heavy_hitters(["a", "b", "c", "d", "e", "f", "g"]) == []
    assert heavy_hitters([]) == []


def test_one_frequent_word_among_many_rare_ones() -> None:
    """Returns only the word that clears the bar, not the other survivor."""
    assert heavy_hitters(["a", "x", "a", "y", "a", "z", "w"]) == ["a"]
    assert heavy_hitters(["k", "a", "a"]) == ["a"]


def test_a_word_is_not_counted_in_both_slots() -> None:
    """Does not report one word twice when it could fill both candidate slots."""
    assert heavy_hitters(["a", "b", "c", "a", "a"]) == ["a"]
    assert heavy_hitters(["a", "a", "a"]) == ["a"]
    assert heavy_hitters(["a", "b", "b", "a", "a", "a"]) == ["a"]


def test_frequent_words_survive_being_outnumbered_early() -> None:
    """Finds words whose copies all come after a run of different ones."""
    assert heavy_hitters(["p", "q", "r", "a", "a", "a", "a", "b", "b", "b", "b"]) == [
        "a",
        "b",
    ]
    assert heavy_hitters(["a", "b", "c", "d", "e", "f", "z", "z", "z", "z", "z"]) == [
        "z"
    ]


def test_compares_words_exactly() -> None:
    """Treats words that differ in case as different words."""
    assert heavy_hitters(["A", "a", "A", "a"]) == ["A", "a"]
    assert heavy_hitters(["", "", "x"]) == [""]


def test_agrees_with_counting_every_word() -> None:
    """Matches a full tally for every short list.

    Every list of up to eight words drawn from a, b, c, d.
    """
    for size in range(9):
        for chosen in product("abcd", repeat=size):
            words = list(chosen)
            assert heavy_hitters(words) == by_counting(words), words


def test_leaves_the_list_alone() -> None:
    """Does not reorder or modify the list it was given."""
    words = ["b", "a", "b"]

    heavy_hitters(words)

    assert words == ["b", "a", "b"]


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the number of different words.

    A hundred thousand entries: forty thousand copies of one word, and sixty
    thousand words that each appear once, mixed through it. A dict of counts
    holds sixty thousand entries, and sorting the list needs a copy of it.
    The list is built before measuring starts.
    """
    words = []
    for index in range(20_000):
        words += ["common", f"rare{3 * index}", "common", f"rare{3 * index + 1}"]
        words.append(f"rare{3 * index + 2}")

    tracemalloc.start()
    found = heavy_hitters(words)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert found == ["common"]
    assert peak < 64_000, f"allocated {peak} bytes"
