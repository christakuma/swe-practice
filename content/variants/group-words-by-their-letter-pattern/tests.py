"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import group_by_pattern


def renames_to(first: str, second: str) -> bool:
    """Whether a consistent one-to-one renaming of letters turns one into the other."""
    if len(first) != len(second):
        return False
    pairs = set(zip(first, second, strict=True))
    return len(pairs) == len({a for a, _ in pairs}) == len({b for _, b in pairs})


def by_comparing_pairs(words: list[str]) -> list[list[str]]:
    """Put each word in the first group whose first word it can be renamed to."""
    groups: list[list[str]] = []
    for word in words:
        for group in groups:
            if renames_to(group[0], word):
                group.append(word)
                break
        else:
            groups.append([word])
    return groups


def test_groups_words_with_the_same_shape() -> None:
    """Groups words whose letters repeat in the same places."""
    words = ["egg", "add", "abc", "too", "xyz"]

    assert group_by_pattern(words) == [["egg", "add", "too"], ["abc", "xyz"]]


def test_anagrams_are_not_grouped_unless_their_shapes_match() -> None:
    """Separates anagrams whose repeated letter is in a different place."""
    assert group_by_pattern(["egg", "gge", "geg"]) == [["egg"], ["gge"], ["geg"]]
    assert group_by_pattern(["abc", "cab"]) == [["abc", "cab"]]


def test_two_letters_may_not_become_one() -> None:
    """Separates a word with distinct letters from one where they coincide."""
    assert group_by_pattern(["ab", "aa", "cd", "zz"]) == [["ab", "cd"], ["aa", "zz"]]


def test_one_letter_may_not_become_two() -> None:
    """Separates in the other direction too, with the repeat arriving first."""
    assert group_by_pattern(["aa", "ab"]) == [["aa"], ["ab"]]
    assert group_by_pattern(["paper", "title", "tests"]) == [
        ["paper", "title"],
        ["tests"],
    ]


def test_different_lengths_are_never_grouped() -> None:
    """Keeps words of different lengths apart."""
    assert group_by_pattern(["a", "bb", "c", "dd", "eee"]) == [
        ["a", "c"],
        ["bb", "dd"],
        ["eee"],
    ]


def test_a_word_has_the_same_pattern_as_itself() -> None:
    """Keeps duplicates, and groups them together."""
    assert group_by_pattern(["ab", "ab", "xy"]) == [["ab", "ab", "xy"]]


def test_empty_strings_share_a_pattern() -> None:
    """Groups empty strings together and apart from everything else."""
    assert group_by_pattern(["", "a", ""]) == [["", ""], ["a"]]


def test_no_words_give_no_groups() -> None:
    """Returns an empty list for no words."""
    assert group_by_pattern([]) == []


def test_keeps_input_order_at_both_levels() -> None:
    """Orders groups by their first word and words by where they appeared."""
    words = ["zz", "abc", "qq", "xyz", "aa", "mno"]

    assert group_by_pattern(words) == [["zz", "qq", "aa"], ["abc", "xyz", "mno"]]


def test_case_and_other_characters_are_just_letters() -> None:
    """Treats any character as a letter, and upper and lower case as different."""
    assert group_by_pattern(["Aa", "bc", "!!", "aA", "11"]) == [
        ["Aa", "bc", "aA"],
        ["!!", "11"],
    ]


def test_handles_more_than_ten_different_letters() -> None:
    """Does not confuse the eleventh letter with the second followed by the first.

    Renaming letters to digits and joining them makes the eleventh letter,
    "10", read the same as the second letter followed by the first.
    """
    eleven = "abcdefghijk"
    lookalike = "abcdefghijba"

    assert group_by_pattern([eleven, lookalike]) == [[eleven], [lookalike]]
    assert group_by_pattern([eleven, "lmnopqrstuv"]) == [[eleven, "lmnopqrstuv"]]


def test_agrees_with_comparing_every_pair() -> None:
    """Matches pairwise renaming checks for every short list of short words.

    Every list of three words, each of one to three letters over "abc".
    """
    vocabulary = [
        "".join(letters)
        for size in (1, 2, 3)
        for letters in product("abc", repeat=size)
    ]
    for chosen in product(vocabulary[::2], repeat=3):
        words = list(chosen)
        assert group_by_pattern(words) == by_comparing_pairs(words), words
    assert group_by_pattern(vocabulary) == by_comparing_pairs(vocabulary)


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    words = ["egg", "add"]

    group_by_pattern(words)

    assert words == ["egg", "add"]


def test_groups_ten_thousand_words() -> None:
    """Groups ten thousand words into the three patterns they share."""
    words = []
    for index in range(10_000):
        a, b = chr(97 + index % 13), chr(110 + index % 11)
        words.append((a + a + b, a + b + a, a + b + b)[index % 3])

    groups = group_by_pattern(words)

    assert [len(group) for group in groups] == [3334, 3333, 3333]
    assert groups[0][:2] == ["aan", "ddq"]
