"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise, permutations, product

from solution import longest_word


def spellable(board: list[list[str]], word: str) -> bool:
    """Try every ordered choice of distinct cells of the right length."""
    cells = [(y, x) for y in range(len(board)) for x in range(len(board[y]))]
    for path in permutations(cells, len(word)):
        letters = all(
            board[y][x] == letter for (y, x), letter in zip(path, word, strict=True)
        )
        if letters and all(
            abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in pairwise(path)
        ):
            return True
    return False


def by_checking_each(board: list[list[str]], words: list[str]) -> str:
    present = [word for word in words if word and spellable(board, word)]
    return min(present, key=lambda word: (-len(word), word), default="")


def test_returns_the_longest_word_present() -> None:
    """Returns the longest of the words that can be spelled."""
    board = [
        ["o", "a", "a", "n"],
        ["e", "t", "a", "e"],
        ["i", "h", "k", "r"],
        ["i", "f", "l", "v"],
    ]

    assert longest_word(board, ["oath", "pea", "eat", "rain", "oat"]) == "oath"


def test_breaks_ties_alphabetically() -> None:
    """Returns the alphabetically first of the longest words."""
    board = [["a", "b"], ["c", "d"]]

    assert longest_word(board, ["bd", "ac", "ab", "abcd"]) == "ab"


def test_skips_a_longer_word_that_cannot_be_spelled() -> None:
    """Passes over longer words that need a diagonal or a reused cell."""
    board = [["a", "b"], ["c", "d"]]

    assert longest_word(board, ["abcd", "aba", "abdc", "a"]) == "abdc"
    assert longest_word(board, ["abcd", "aba", "a"]) == "a"


def test_returns_nothing_when_no_word_is_present() -> None:
    """Returns "" for no match, no words, no board, and the empty word."""
    assert longest_word([["a"]], ["b", ""]) == ""
    assert longest_word([["a"]], []) == ""
    assert longest_word([], ["a"]) == ""


def test_leaves_the_board_as_it_found_it() -> None:
    """Restores the board whether or not a word is found."""
    board = [["a", "b"], ["c", "d"]]

    longest_word(board, ["abdc", "zzz", "abd"])

    assert board == [["a", "b"], ["c", "d"]]


def test_agrees_with_checking_every_word() -> None:
    """Matches a check of every word, for every small grid and word list."""
    pool = ["", "a", "b", "ab", "ba", "aa", "aba", "abb", "bab"]
    for cells in product("ab", repeat=4):
        board = [list(cells[:2]), list(cells[2:])]
        for chosen in product(pool, repeat=2):
            words = list(chosen)
            assert longest_word(board, words) == by_checking_each(board, words), (
                board,
                words,
            )
    for cells in product("ab", repeat=6):
        board = [list(cells[:3]), list(cells[3:])]
        assert longest_word(board, pool) == by_checking_each(board, pool), board
