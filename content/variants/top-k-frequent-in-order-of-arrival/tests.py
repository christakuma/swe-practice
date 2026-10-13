"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import top_k_frequent


def by_positions(words: list[str], k: int) -> list[str]:
    """Rank by count, then by the index of the first occurrence."""
    distinct = set(words)
    return sorted(distinct, key=lambda word: (-words.count(word), words.index(word)))[
        :k
    ]


def test_breaks_ties_by_first_appearance() -> None:
    """Returns equal-count words in the order they arrived."""
    assert top_k_frequent(["pear", "apple", "fig"], 3) == ["pear", "apple", "fig"]


def test_puts_the_more_frequent_word_first() -> None:
    """Orders by count before anything else."""
    assert top_k_frequent(["x", "y", "y"], 1) == ["y"]
    assert top_k_frequent(["x", "y", "y"], 2) == ["y", "x"]


def test_uses_the_first_appearance_not_the_last() -> None:
    """Goes by where a word first turned up, not where it last did."""
    assert top_k_frequent(["b", "a", "a", "b", "c"], 2) == ["b", "a"]
    assert top_k_frequent(["a", "b", "b", "a"], 2) == ["a", "b"]


def test_handles_nothing_asked_for() -> None:
    """Returns an empty list for k = 0 and for no words."""
    assert top_k_frequent(["a", "b"], 0) == []
    assert top_k_frequent([], 0) == []


def test_agrees_with_ranking_by_position() -> None:
    """Matches a count-then-position ranking for every short list and every k."""
    for length in range(7):
        for chosen in product("cab", repeat=length):
            words = list(chosen)
            for k in range(len(set(words)) + 1):
                assert top_k_frequent(words, k) == by_positions(words, k), (words, k)


def test_leaves_the_list_alone() -> None:
    """Does not sort or modify the list it was given."""
    words = ["b", "a", "b"]

    top_k_frequent(words, 1)

    assert words == ["b", "a", "b"]


def test_ranks_a_long_list() -> None:
    """Ranks a hundred thousand words within the time limit."""
    words = [f"w{index % 5000:04d}" for index in range(100_000)]
    words += ["late"] * 21

    assert top_k_frequent(words, 3) == ["late", "w0000", "w0001"]
