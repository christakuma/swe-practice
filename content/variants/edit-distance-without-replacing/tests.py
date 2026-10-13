"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import edit_distance


def is_subsequence(short: str, long: str) -> bool:
    remaining = iter(long)
    return all(character in remaining for character in short)


def by_longest_shared_subsequence(source: str, target: str) -> int:
    """Everything not in the longest common subsequence is deleted or inserted."""
    for size in range(len(source), -1, -1):
        for kept in combinations(source, size):
            if is_subsequence("".join(kept), target):
                return len(source) + len(target) - 2 * size
    raise AssertionError("the empty subsequence is always shared")


def test_identical_strings_need_no_edits() -> None:
    """Returns 0 when the strings are already equal."""
    assert edit_distance("kitten", "kitten") == 0
    assert edit_distance("", "") == 0


def test_inserting_or_deleting_everything() -> None:
    """Returns the other string's length when one string is empty."""
    assert edit_distance("", "abc") == 3
    assert edit_distance("abcd", "") == 4


def test_a_changed_character_costs_two() -> None:
    """Charges a deletion and an insertion where a replace would have done."""
    assert edit_distance("cat", "cut") == 2
    assert edit_distance("a", "b") == 2
    assert edit_distance("abc", "xyz") == 6


def test_a_single_insertion_or_deletion_costs_one() -> None:
    """Charges one edit for one character added or removed, wherever it is."""
    assert edit_distance("cat", "cart") == 1
    assert edit_distance("cart", "cat") == 1
    assert edit_distance("at", "cat") == 1
    assert edit_distance("cat", "ca") == 1


def test_keeps_characters_that_are_in_order_in_both() -> None:
    """Keeps a shared subsequence even when it is not contiguous."""
    assert edit_distance("sea", "eat") == 2
    assert edit_distance("abcde", "ace") == 2
    assert edit_distance("intention", "execution") == 8


def test_order_matters() -> None:
    """Does not treat the same letters in a different order as equal."""
    assert edit_distance("ab", "ba") == 2
    assert edit_distance("abc", "cba") == 4


def test_is_symmetric() -> None:
    """Gives the same distance in both directions."""
    assert edit_distance("flaw", "lawn") == edit_distance("lawn", "flaw") == 2


def test_compares_characters_exactly() -> None:
    """Treats upper and lower case as different characters."""
    assert edit_distance("a", "A") == 2


def test_agrees_with_the_longest_shared_subsequence() -> None:
    """Matches a brute-force longest common subsequence for every short pair.

    Every pair of strings of up to five characters over "ab", and up to four
    over "abc".
    """
    for alphabet, longest in (("ab", 5), ("abc", 4)):
        words = [
            "".join(letters)
            for size in range(longest + 1)
            for letters in product(alphabet, repeat=size)
        ]
        for source in words:
            for target in words:
                expected = by_longest_shared_subsequence(source, target)
                assert edit_distance(source, target) == expected, (source, target)


def test_handles_strings_of_five_hundred_characters() -> None:
    """Fills a 500 x 500 table within the time limit.

    One string is "ab" repeated and the other "ba" repeated. Dropping the
    first character of one and the last of the other leaves them equal.
    """
    assert edit_distance("ab" * 250, "ba" * 250) == 2
    assert edit_distance("a" * 500, "b" * 500) == 1000
