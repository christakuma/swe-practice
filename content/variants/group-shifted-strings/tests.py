"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import group_shifted

POOL = ["", "a", "z", "ab", "bc", "za", "ac", "ba", "abc", "bcd", "xyz", "abd"]


def shifted(word: str, steps: int) -> str:
    return "".join(chr((ord(letter) - 97 + steps) % 26 + 97) for letter in word)


def by_trying_every_shift(words: list[str]) -> list[list[str]]:
    """Put each word in the first group whose first member it is a shift of."""
    groups: list[list[str]] = []
    for word in words:
        for group in groups:
            if any(shifted(group[0], steps) == word for steps in range(26)):
                group.append(word)
                break
        else:
            groups.append([word])
    return groups


def test_groups_the_documented_words() -> None:
    """Groups the worked example."""
    words = ["abc", "bcd", "acef", "xyz", "az", "ba", "a", "z"]

    assert group_shifted(words) == [
        ["abc", "bcd", "xyz"],
        ["acef"],
        ["az", "ba"],
        ["a", "z"],
    ]


def test_wraps_round_the_alphabet() -> None:
    """Groups words whose shift carries a letter past z."""
    assert group_shifted(["az", "ba"]) == [["az", "ba"]]
    assert group_shifted(["yza", "abc"]) == [["yza", "abc"]]


def test_does_not_group_anagrams() -> None:
    """Keeps anagrams apart when they are not shifts."""
    assert group_shifted(["ab", "ba"]) == [["ab"], ["ba"]]


def test_keeps_input_order() -> None:
    """Orders groups, and the words inside them, by first appearance."""
    assert group_shifted(["bc", "x", "ab", "y"]) == [["bc", "ab"], ["x", "y"]]


def test_handles_duplicates_and_empty_strings() -> None:
    """Groups repeated words and empty strings rather than dropping them."""
    assert group_shifted(["ab", "ab"]) == [["ab", "ab"]]
    assert group_shifted(["", "a", ""]) == [["", ""], ["a"]]
    assert group_shifted([]) == []


def test_agrees_with_trying_every_shift() -> None:
    """Matches a try-all-26-shifts grouping for every short list from a pool."""
    for size in range(4):
        for chosen in product(POOL, repeat=size):
            words = list(chosen)
            assert group_shifted(words) == by_trying_every_shift(words), words


def test_groups_a_long_list() -> None:
    """Groups ten thousand words within the time limit."""
    words = [shifted("practice", index % 26) for index in range(10_000)]

    assert group_shifted(words) == [words]
