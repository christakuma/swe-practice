"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import longest_shared_prefix

POOL = ["", "a", "b", "ab", "aa", "ba", "abc", "abd", "bab", "bac"]


def shared(first: str, second: str) -> str:
    length = 0
    while length < min(len(first), len(second)) and first[length] == second[length]:
        length += 1
    return first[:length]


def by_every_pair(words: list[str]) -> str:
    candidates = [shared(a, b) for a, b in combinations(words, 2)]
    return min(candidates, key=lambda text: (-len(text), text), default="")


def test_finds_a_prefix_two_words_share() -> None:
    """Returns a prefix shared by two words that the others do not have."""
    words = ["flower", "dog", "flight", "dorm", "flow"]

    assert longest_shared_prefix(words) == "flow"


def test_returns_nothing_when_no_two_words_agree() -> None:
    """Returns the empty string when every first character differs."""
    assert longest_shared_prefix(["apple", "bat", "cat"]) == ""


def test_needs_two_words() -> None:
    """Returns the empty string for no words and for one."""
    assert longest_shared_prefix([]) == ""
    assert longest_shared_prefix(["solo"]) == ""


def test_counts_a_repeated_word_as_two() -> None:
    """Treats two equal entries as sharing the whole string."""
    assert longest_shared_prefix(["ab", "ab"]) == "ab"


def test_breaks_ties_alphabetically() -> None:
    """Returns the alphabetically first of the longest shared prefixes."""
    assert longest_shared_prefix(["zebra", "zest", "anchor", "ankle"]) == "an"


def test_agrees_with_comparing_every_pair() -> None:
    """Matches an every-pair search for every short list from a pool."""
    for size in range(5):
        for chosen in product(POOL, repeat=size):
            words = list(chosen)
            assert longest_shared_prefix(words) == by_every_pair(words), words


def test_leaves_the_list_alone() -> None:
    """Does not sort the caller's list."""
    words = ["b", "a", "ab"]

    longest_shared_prefix(words)

    assert words == ["b", "a", "ab"]


def test_handles_a_hundred_thousand_words() -> None:
    """Handles a hundred thousand words within the time limit."""
    words = [f"{number:06d}" for number in reversed(range(100_000))]

    assert longest_shared_prefix(words) == "00000"
