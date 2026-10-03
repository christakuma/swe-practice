"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import top_k_frequent


def test_returns_the_most_frequent_word() -> None:
    """Returns the single most frequent word."""
    assert top_k_frequent(["a", "b", "a"], 1) == ["a"]


def test_orders_by_count_descending() -> None:
    """Puts the more frequent word first."""
    assert top_k_frequent(["b", "a", "a", "b", "a"], 2) == ["a", "b"]


def test_breaks_ties_alphabetically() -> None:
    """Orders words with equal counts alphabetically.

    Every word here appears once, so the whole result is the tie-break. A
    solution leaning on `Counter.most_common` returns insertion order and gets
    `["pear", "apple", "fig"]`.
    """
    assert top_k_frequent(["pear", "apple", "fig"], 3) == ["apple", "fig", "pear"]


def test_does_not_reverse_the_tie_break() -> None:
    """Keeps ties alphabetical while counts descend.

    `sorted(..., key=count, reverse=True)` reverses *both* parts of the
    ordering, so this comes back as `["zebra", "ant"]` for the tied pair.
    """
    assert top_k_frequent(["cat", "cat", "zebra", "ant"], 3) == ["cat", "ant", "zebra"]


def test_returns_fewer_than_k_is_never_asked() -> None:
    """Returns exactly k words when k is the number of distinct words."""
    assert top_k_frequent(["x", "y"], 2) == ["x", "y"]


def test_handles_k_of_zero() -> None:
    """Returns nothing when asked for nothing."""
    assert top_k_frequent(["a", "b"], 0) == []


def test_handles_an_empty_list() -> None:
    """Returns nothing for no words."""
    assert top_k_frequent([], 0) == []


def test_handles_one_word_repeated() -> None:
    """Counts a single repeated word correctly."""
    assert top_k_frequent(["z", "z", "z"], 1) == ["z"]


def test_handles_a_large_vocabulary_quickly() -> None:
    """Ranks a long list with many distinct words.

    Thirty thousand words over ten thousand distinct ones, where the counts
    descend in blocks of three. A solution that re-scans the list to count each
    candidate is quadratic.
    """
    words = [f"w{index // 3:05d}" for index in range(30_000)]

    assert top_k_frequent(words, 3) == ["w00000", "w00001", "w00002"]
