"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement, pairwise, permutations, product

from solution import alien_order


def reference(words: list[str]) -> str:
    """The smallest permutation of the alphabet under which `words` is sorted.

    An independent oracle: it builds no graph and does no topological sort, it
    just tries every alphabet in order and returns the first that works.
    Factorial, and fine for three or four characters.
    """
    characters = sorted({character for word in words for character in word})
    for candidate in permutations(characters):
        rank = {character: index for index, character in enumerate(candidate)}

        def key(word: str, rank: dict[str, int] = rank) -> list[int]:
            return [rank[character] for character in word]

        if all(key(a) <= key(b) for a, b in pairwise(words)):
            return "".join(candidate)
    return ""


def test_handles_the_worked_example() -> None:
    """Returns the alphabet implied by the documented words."""
    assert alien_order(["wrt", "wrf", "er", "ett", "rftt"]) == "wertf"


def test_handles_a_single_constraint() -> None:
    """Orders two characters from one word pair."""
    assert alien_order(["z", "x"]) == "zx"


def test_rejects_a_cycle() -> None:
    """Returns "" when the constraints contradict each other.

    z before x and x before z. A solution that topologically sorts without
    checking it emitted every character returns a partial order instead.
    """
    assert alien_order(["z", "x", "z"]) == ""
    assert alien_order(["ab", "ba", "ab"]) == ""


def test_rejects_a_word_followed_by_its_own_prefix() -> None:
    """Returns "" when a longer word precedes its own prefix.

    No alphabet sorts "abc" before "ab". This pair implies **no edges at all**,
    so a solution that only builds a graph and sorts it returns a plausible
    ordering for input that cannot exist.
    """
    assert alien_order(["abc", "ab"]) == ""
    assert alien_order(["ab", "a"]) == ""
    assert alien_order(["xy", "xyz", "xy"]) == ""


def test_accepts_a_prefix_in_the_right_order() -> None:
    """Accepts a shorter word before its own extension."""
    assert alien_order(["ab", "abc"]) == "abc"
    assert alien_order(["a", "ab", "abc"]) == "abc"


def test_handles_an_empty_input() -> None:
    """Returns "" when there are no words."""
    assert alien_order([]) == ""


def test_handles_a_single_word() -> None:
    """Returns the word's characters when nothing constrains them.

    Only one word, so there are no comparisons -- every character is
    unconstrained and the smallest valid order is simply sorted.
    """
    assert alien_order(["abc"]) == "abc"
    assert alien_order(["cba"]) == "abc"
    assert alien_order(["z"]) == "z"


def test_handles_repeated_words() -> None:
    """Accepts the same word twice, which constrains nothing."""
    assert alien_order(["ab", "ab"]) == "ab"
    assert alien_order(["ab", "ab", "ac"]) == "abc"


def test_includes_unconstrained_characters() -> None:
    """Includes characters that no comparison mentions.

    The pair only constrains a before b; c and d appear but are never
    compared, and must still show up exactly once.
    """
    assert alien_order(["acd", "bcd"]) == "abcd"


def test_takes_only_the_first_difference_from_each_pair() -> None:
    """Derives one constraint per word pair, not several.

    "ab" before "ba" says only that a precedes b. Reading the second position
    as well would also claim b precedes a, which is a cycle -- so a solution
    that does not stop at the first difference reports "" here.
    """
    assert alien_order(["ab", "ba"]) == "ab"


def test_returns_the_smallest_valid_order() -> None:
    """Chooses the lexicographically smallest of several valid orders.

    In the first, nothing relates b to c, so "abc" and "acb" are both
    consistent and the smaller is required. A plain queue in place of a
    min-heap gives whichever the insertion order happened to produce.

    The second is the sharper case: c must precede a, and b is unconstrained.
    So plain sorted order "abc" is *invalid*, and the smallest valid answer
    puts the unconstrained b first -- which no amount of sorting the output
    produces. It has to come from taking the smallest available character at
    each step.
    """
    assert alien_order(["ab", "ac"]) == "abc"
    assert alien_order(["ca", "ab"]) == "bca"


def test_handles_duplicate_constraints() -> None:
    """Counts a repeated constraint once.

    Several word pairs imply a before b. Incrementing the in-degree per
    occurrence leaves b never reaching zero, so a valid input reports "".
    """
    assert alien_order(["ax", "bx", "ay", "by"]) == ""
    assert alien_order(["ax", "bx", "by", "bz"]) == "abxyz"


def test_returns_a_string() -> None:
    """Returns a str rather than a list of characters."""
    assert type(alien_order(["z", "x"])) is str


def test_includes_every_character_exactly_once() -> None:
    """Returns each distinct character once and nothing else."""
    words = ["wrt", "wrf", "er", "ett", "rftt"]
    expected = {character for word in words for character in word}

    result = alien_order(words)

    assert set(result) == expected
    assert len(result) == len(expected)


def test_agrees_with_a_permutation_search_on_short_words() -> None:
    """Matches the brute-force oracle for every short word list over a, b, c.

    Every list of up to three words drawn from the one- and two-character
    words -- around two thousand cases. The prefix rule, the first-difference
    rule and the duplicate-edge handling each need particular inputs.
    """
    pool = [
        "".join(characters)
        for length in (1, 2)
        for characters in product("abc", repeat=length)
    ]
    for count in range(4):
        for words in product(pool, repeat=count):
            given = list(words)

            assert alien_order(given) == reference(given), given


def test_agrees_with_a_permutation_search_on_three_character_words() -> None:
    """Matches the oracle for pairs and triples of three-character words.

    Longer words are where "stop at the first difference" is load-bearing: a
    pair can agree for two positions and differ at the third.
    """
    pool = ["".join(characters) for characters in product("abc", repeat=3)]
    for count in (2, 3):
        for chosen in combinations_with_replacement(pool, count):
            for ordering in set(permutations(chosen)):
                given = list(ordering)

                assert alien_order(given) == reference(given), given
