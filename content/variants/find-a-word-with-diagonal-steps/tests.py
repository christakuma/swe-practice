"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise, permutations, product

from solution import exists


def by_every_path(board: list[list[str]], word: str) -> bool:
    """Try every ordered choice of distinct cells of the right length."""
    cells = [(y, x) for y in range(len(board)) for x in range(len(board[y]))]
    for path in permutations(cells, len(word)):
        if all(
            board[y][x] == letter for (y, x), letter in zip(path, word, strict=True)
        ) and all(
            abs(a[0] - b[0]) <= 1 and abs(a[1] - b[1]) <= 1 for a, b in pairwise(path)
        ):
            return True
    return False


def test_steps_diagonally() -> None:
    """Finds a word that needs a diagonal step."""
    assert exists([["A", "B"], ["C", "D"]], "AD") is True
    assert exists([["A", "B", "C"], ["D", "E", "F"]], "AEC") is True


def test_still_cannot_reuse_a_cell() -> None:
    """Rejects a word that would need the same cell twice."""
    assert exists([["A", "B"], ["C", "D"]], "ADA") is False


def test_still_needs_adjacent_cells() -> None:
    """Rejects a word whose letters are present but not next to each other."""
    assert exists([["A", "B", "C"]], "AC") is False


def test_handles_empty_words_and_boards() -> None:
    """Finds the empty word anywhere, and nothing else on an empty board."""
    assert exists([], "") is True
    assert exists([["A"]], "") is True
    assert exists([], "A") is False


def test_leaves_the_board_as_it_found_it() -> None:
    """Restores the board on success and on failure."""
    board = [["A", "B"], ["C", "D"]]

    exists(board, "ADBC")
    exists(board, "ADX")

    assert board == [["A", "B"], ["C", "D"]]


def test_agrees_with_trying_every_path() -> None:
    """Matches an every-path search for every 2x2 and 2x3 grid over two letters."""
    words = [
        "".join(letters)
        for size in range(1, 5)
        for letters in product("AB", repeat=size)
    ]
    for columns in (2, 3):
        for cells in product("AB", repeat=2 * columns):
            board = [list(cells[:columns]), list(cells[columns:])]
            for word in words:
                expected = by_every_path(board, word)
                assert exists(board, word) is expected, (board, word)
