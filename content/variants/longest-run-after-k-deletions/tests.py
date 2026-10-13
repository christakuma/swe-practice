"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_run


def by_trying_every_stretch(text: str, k: int) -> int:
    """The answer by pricing every stretch for every character. An oracle.

    A stretch that starts and ends with the character costs its width less
    the number of that character in it, and yields that number.
    """
    best = 0
    for start in range(len(text)):
        kept = 0
        for end in range(start, len(text)):
            if text[end] == text[start]:
                kept += 1
                if (end - start + 1) - kept <= k:
                    best = max(best, kept)
    return best


def test_deleting_closes_a_gap() -> None:
    """Joins two runs by deleting what is between them."""
    assert longest_run("aabaa", 1) == 4


def test_a_deleted_character_does_not_count_towards_the_run() -> None:
    """Returns the characters kept, not the width of the stretch they came from."""
    assert longest_run("abcabc", 2) == 2
    assert longest_run("abba", 2) == 2
    assert longest_run("xaxax", 2) == 3


def test_with_no_deletions_returns_the_longest_existing_run() -> None:
    """Returns the longest run already present when k is zero."""
    assert longest_run("abab", 0) == 1
    assert longest_run("aabbbcc", 0) == 3
    assert longest_run("zzzz", 0) == 4


def test_handles_an_empty_string() -> None:
    """Returns zero for an empty string, whatever k is."""
    assert longest_run("", 0) == 0
    assert longest_run("", 3) == 0


def test_unused_deletions_cost_nothing() -> None:
    """Returns the whole run when there is nothing that needs deleting.

    The replacement answer minus k gets this wrong: it assumes all of k was
    spent.
    """
    assert longest_run("aaa", 1) == 3
    assert longest_run("aaa", 5) == 3
    assert longest_run("aab", 2) == 2


def test_k_larger_than_the_string_keeps_the_commonest_character() -> None:
    """Returns the count of the commonest character when everything else can go."""
    assert longest_run("abcabca", 100) == 3
    assert longest_run("mississippi", 100) == 4


def test_cannot_afford_a_gap_wider_than_k() -> None:
    """Does not join runs that are more than k characters apart."""
    assert longest_run("aabbbaa", 2) == 3
    assert longest_run("aabbbaa", 3) == 4
    assert longest_run("abbbbbba", 5) == 6


def test_may_spend_on_several_gaps() -> None:
    """Deletes from more than one gap when together they cost no more than k."""
    assert longest_run("abacada", 3) == 4
    assert longest_run("abacada", 2) == 3


def test_the_best_character_is_not_always_the_commonest() -> None:
    """Chooses a rarer character whose copies are close together.

    There are four a's and three b's. The a's are two characters apart, so
    one deletion joins none of them; it joins all three b's.
    """
    assert longest_run("a12a34a56abbcb", 1) == 3


def test_case_matters() -> None:
    """Does not count an upper-case letter as its lower-case form."""
    assert longest_run("aAa", 0) == 1
    assert longest_run("aAa", 1) == 2


def test_agrees_with_pricing_every_stretch() -> None:
    """Matches a check of every stretch for every short string and every k.

    Every string of up to eight characters over a, b and c, and every k from
    zero to four.
    """
    for size in range(9):
        for letters in product("abc", repeat=size):
            text = "".join(letters)
            for k in range(5):
                assert longest_run(text, k) == by_trying_every_stretch(text, k), (
                    text,
                    k,
                )


def test_handles_thousands_of_different_characters() -> None:
    """Scans two hundred thousand characters drawn from four thousand.

    The same four thousand characters repeat in the same order fifty times,
    so copies of any one are 3,999 apart, and joining m of them costs
    3,999 * (m - 1). With 20,000 deletions that is six copies, and with
    none it is one.

    A scan of the whole string for each character in turn is four thousand
    scans, which is what this is sized to rule out.
    """
    alphabet = "".join(chr(0x4E00 + offset) for offset in range(4_000))
    text = alphabet * 50

    assert longest_run(text, 20_000) == 6
    assert longest_run(text, 0) == 1


def test_handles_a_long_string() -> None:
    """Scans half a million characters.

    Blocks of nine a's separated by a single b: each deletion joins another
    nine.
    """
    text = ("a" * 9 + "b") * 50_000

    assert longest_run(text, 10) == 9 * 11
    assert longest_run(text, 10**6) == 9 * 50_000
