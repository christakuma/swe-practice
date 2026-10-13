"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import shortest_unique_prefixes


def by_definition(words: list[str]) -> list[str]:
    """Each word's answer straight from the definition. An oracle.

    Tries each prefix in turn against every other position in the list.
    """
    answers = []
    for position, word in enumerate(words):
        others = words[:position] + words[position + 1 :]
        for length in range(1, len(word) + 1):
            if not any(other.startswith(word[:length]) for other in others):
                answers.append(word[:length])
                break
        else:
            answers.append(word)
    return answers


def test_gives_one_letter_where_one_is_enough() -> None:
    """Returns a single character for a word that shares its first with nothing."""
    assert shortest_unique_prefixes(["zebra", "dog", "duck", "dove"]) == [
        "z",
        "dog",
        "du",
        "dov",
    ]


def test_goes_one_past_the_longest_shared_stretch() -> None:
    """Returns one more character than the word shares with its closest rival."""
    assert shortest_unique_prefixes(["interview", "internet", "interval"]) == [
        "intervi",
        "intern",
        "interva",
    ]


def test_a_word_alone_needs_one_character() -> None:
    """Returns the first character of the only word, not an empty prefix."""
    assert shortest_unique_prefixes(["apple"]) == ["a"]


def test_handles_an_empty_list() -> None:
    """Returns an empty list for no words."""
    assert shortest_unique_prefixes([]) == []


def test_returns_a_word_whole_when_another_word_starts_with_it() -> None:
    """Returns the whole word when every prefix of it begins a longer word."""
    assert shortest_unique_prefixes(["car", "cart", "cat"]) == ["car", "cart", "cat"]
    assert shortest_unique_prefixes(["a", "ab", "abc"]) == ["a", "ab", "abc"]


def test_returns_a_repeated_word_whole_each_time() -> None:
    """Returns the whole word at every position it appears.

    Collapsing the list to its distinct words first loses this: "hello"
    would then be the only word starting with h, and get one letter.
    """
    assert shortest_unique_prefixes(["hello", "hello", "world"]) == [
        "hello",
        "hello",
        "w",
    ]
    assert shortest_unique_prefixes(["go", "go", "gone"]) == ["go", "go", "gon"]
    assert shortest_unique_prefixes(["x", "x"]) == ["x", "x"]
    assert shortest_unique_prefixes(["bat", "ball", "bat"]) == ["bat", "bal", "bat"]


def test_keeps_the_order_the_words_came_in() -> None:
    """Returns each prefix at its own word's position, not in sorted order."""
    assert shortest_unique_prefixes(["mud", "apple", "mug", "ant"]) == [
        "mud",
        "ap",
        "mug",
        "an",
    ]


def test_the_closest_word_may_sort_on_either_side() -> None:
    """Compares with the word before and the word after in sorted order.

    "bc" shares nothing with "a" before it and one letter with "bd" after;
    "bd" shares one with "bc" before it and nothing with "c" after.
    """
    assert shortest_unique_prefixes(["a", "bc", "bd", "c"]) == ["a", "bc", "bd", "c"]
    assert shortest_unique_prefixes(["abcx", "abd", "b"]) == ["abc", "abd", "b"]
    assert shortest_unique_prefixes(["a", "bcd", "bce"]) == ["a", "bcd", "bce"]


def test_handles_the_empty_word() -> None:
    """Returns the empty string for an empty word, which everything starts with."""
    assert shortest_unique_prefixes(["", "a"]) == ["", "a"]
    assert shortest_unique_prefixes([""]) == [""]
    assert shortest_unique_prefixes(["", "", "ab"]) == ["", "", "a"]


def test_compares_case_exactly() -> None:
    """Treats upper and lower case as different characters."""
    assert shortest_unique_prefixes(["Apple", "apple", "apply"]) == [
        "A",
        "apple",
        "apply",
    ]


def test_leaves_the_list_as_it_was() -> None:
    """Does not sort or otherwise change the list it was given."""
    words = ["pear", "peach", "apple"]

    shortest_unique_prefixes(words)

    assert words == ["pear", "peach", "apple"]


def test_agrees_with_the_definition_on_every_short_list() -> None:
    """Matches a prefix-by-prefix check on every list of up to four short words.

    The words are every string of up to three letters over a and b, the
    empty one included, so prefixes of each other and repeats are everywhere.
    """
    vocabulary = [
        "".join(letters) for size in range(4) for letters in product("ab", repeat=size)
    ]
    for count in range(1, 4):
        for words in product(vocabulary, repeat=count):
            assert shortest_unique_prefixes(list(words)) == by_definition(
                list(words)
            ), words
    for words in product(vocabulary[:7], repeat=4):
        assert shortest_unique_prefixes(list(words)) == by_definition(list(words)), (
            words
        )


def test_handles_twenty_thousand_words_without_comparing_every_pair() -> None:
    """Finds twenty thousand prefixes within the time limit.

    Every word is a five-digit number followed by the same tail, and every
    number has another in the list that differs only in its last digit. So
    each needs exactly its five digits, and the answer is known without
    computing it. Two hundred million pairs is what this is sized to rule
    out.
    """
    count = 20_000
    numbers = [f"{position * 7_919 % count:05d}" for position in range(count)]

    assert len(set(numbers)) == count
    assert shortest_unique_prefixes([number + "-tail" for number in numbers]) == numbers
