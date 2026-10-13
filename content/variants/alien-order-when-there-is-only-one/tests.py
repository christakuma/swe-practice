"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise, permutations, product

from solution import alien_order


def consistent_orders(words: list[str]) -> list[str]:
    """Every alphabet under which the words are sorted, by trying them all."""
    characters = sorted({character for word in words for character in word})
    found = []
    for candidate in permutations(characters):
        rank = {character: position for position, character in enumerate(candidate)}
        keys = [[rank[character] for character in word] for word in words]
        if all(earlier <= later for earlier, later in pairwise(keys)):
            found.append("".join(candidate))
    return found


def test_returns_an_order_that_is_fully_determined() -> None:
    """Returns the alphabet when the words leave no choice."""
    assert alien_order(["wrt", "wrf", "er", "ett", "rftt"]) == "wertf"
    assert alien_order(["z", "x"]) == "zx"
    assert alien_order(["c", "b", "a"]) == "cba"


def test_refuses_when_a_character_is_unconstrained() -> None:
    """Returns "" when some character could go anywhere."""
    assert alien_order(["ab", "ac"]) == ""
    assert alien_order(["abc"]) == ""
    assert alien_order(["x", "y", "yz"]) == ""


def test_refuses_when_the_choice_opens_up_later() -> None:
    """Returns "" when the first character is forced and the next two are not.

    a < b and a < c, with nothing between b and c: one character is available
    at the start and two after it.
    """
    assert alien_order(["ab", "ba", "bc"]) == ""


def test_refuses_two_separate_chains() -> None:
    """Returns "" when the characters fall into two unrelated chains."""
    assert alien_order(["ab", "ac", "db", "dc"]) == ""


def test_returns_nothing_for_a_cycle() -> None:
    """Returns "" when the constraints contradict each other."""
    assert alien_order(["b", "a", "b"]) == ""
    assert alien_order(["a", "b", "c", "a"]) == ""


def test_returns_nothing_for_a_word_before_its_own_prefix() -> None:
    """Returns "" when a word is followed by a proper prefix of itself.

    In both lists the other pairs settle the order completely, so the prefix
    is the only thing wrong with them.
    """
    assert alien_order(["zz", "z"]) == ""
    assert alien_order(["a", "b", "bb", "b"]) == ""


def test_one_character_has_one_order() -> None:
    """Returns the character when there is only one, however often it appears."""
    assert alien_order(["z"]) == "z"
    assert alien_order(["zz", "zzz"]) == "z"
    assert alien_order(["q", "q"]) == "q"


def test_no_words_have_one_order_and_it_is_empty() -> None:
    """Returns "" for no words, which is the one ordering of no characters."""
    assert alien_order([]) == ""


def test_counts_an_edge_once_however_often_it_is_implied() -> None:
    """Handles the same constraint arriving from several pairs of words."""
    assert alien_order(["ab", "ac", "bb", "bc", "ca"]) == "abc"


def test_agrees_with_trying_every_alphabet() -> None:
    """Matches a search of every permutation for every small input.

    Every list of up to three words, each one or two characters over "abc".
    """
    vocabulary = [
        "".join(letters) for n in (1, 2) for letters in product("abc", repeat=n)
    ]
    checked = 0
    for size in range(1, 4):
        for chosen in product(vocabulary, repeat=size):
            words = list(chosen)
            orders = consistent_orders(words)
            expected = orders[0] if len(orders) == 1 else ""
            assert alien_order(words) == expected, words
            checked += len(orders) == 1
    assert checked > 100
