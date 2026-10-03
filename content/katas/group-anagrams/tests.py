"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import group_anagrams


def test_groups_words_that_are_anagrams() -> None:
    """Puts anagrams together and everything else apart."""
    assert group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"]) == [
        ["eat", "tea", "ate"],
        ["tan", "nat"],
        ["bat"],
    ]


def test_keeps_input_order_within_a_group() -> None:
    """Orders the words in a group by where they appeared."""
    assert group_anagrams(["tea", "eat", "ate"]) == [["tea", "eat", "ate"]]


def test_orders_groups_by_their_first_word() -> None:
    """Orders the groups by where each group's first word appeared."""
    assert group_anagrams(["bat", "tab", "cat"]) == [["bat", "tab"], ["cat"]]


def test_handles_an_empty_list() -> None:
    """Returns no groups for no words."""
    assert group_anagrams([]) == []


def test_handles_a_single_word() -> None:
    """Returns one group of one."""
    assert group_anagrams(["solo"]) == [["solo"]]


def test_keeps_duplicates_as_separate_entries() -> None:
    """Treats a repeated word as two words in the same group.

    A solution keyed on a set of letters rather than a count, or one that
    deduplicates on the way in, loses one of these.
    """
    assert group_anagrams(["ab", "ab", "ba"]) == [["ab", "ab", "ba"]]


def test_distinguishes_words_with_the_same_letters_in_different_counts() -> None:
    """Separates words whose letter sets match but whose counts do not.

    `aab` and `abb` use the same two letters and are not anagrams. A key built
    from `set(word)` groups them together and passes every other test here.
    """
    assert group_anagrams(["aab", "abb"]) == [["aab"], ["abb"]]


def test_handles_the_empty_string_as_a_word() -> None:
    """Groups empty strings together rather than discarding them."""
    assert group_anagrams(["", "a", ""]) == [["", ""], ["a"]]


def test_groups_many_words_quickly() -> None:
    """Groups a list far too long to compare every pair of words.

    Four thousand words in two groups. Comparing every pair is eight million
    comparisons; keying each word once is four thousand sorts of three
    characters.
    """
    words = ["abc", "cba"] * 2000

    groups = group_anagrams(words)

    assert len(groups) == 1
    assert len(groups[0]) == 4000
