"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import exists

BOARD = [
    ["c", "a", "t", "s"],
    ["x", "o", "r", "e"],
    ["d", "i", "g", "a"],
    ["p", "e", "n", "t"],
]


def lines(board: list[list[str]]) -> list[str]:
    """Every row, column and diagonal of the board, as a string."""
    rows, columns = len(board), len(board[0])
    found = ["".join(row) for row in board]
    found += [
        "".join(board[row][column] for row in range(rows)) for column in range(columns)
    ]
    for total in range(rows + columns - 1):
        cells = [
            (row, total - row) for row in range(rows) if 0 <= total - row < columns
        ]
        found.append("".join(board[row][column] for row, column in cells))
        found.append("".join(board[row][columns - 1 - column] for row, column in cells))
    return found


def in_some_line(board: list[list[str]], word: str) -> bool:
    return any(word in line or word in line[::-1] for line in lines(board))


def test_finds_a_word_across_and_down() -> None:
    """Finds words reading left to right and top to bottom."""
    assert exists(BOARD, "cats")
    assert exists(BOARD, "pent")
    assert exists(BOARD, "seat")
    assert exists(BOARD, "aoie")


def test_finds_a_word_backwards() -> None:
    """Finds words reading right to left and bottom to top."""
    assert exists(BOARD, "stac")
    assert exists(BOARD, "taes")
    assert exists(BOARD, "gid")


def test_finds_a_word_on_a_diagonal() -> None:
    """Finds words along both diagonals, in both directions."""
    assert exists(BOARD, "cogt")
    assert exists(BOARD, "tgoc")
    assert exists(BOARD, "srip")
    assert exists(BOARD, "pirs")
    assert exists(BOARD, "ara")


def test_rejects_a_path_that_bends() -> None:
    """Rejects a word whose letters are adjacent but not in a line."""
    assert not exists(BOARD, "cao")
    assert not exists(BOARD, "catr")
    assert not exists([["c", "a", "x"], ["x", "t", "x"]], "cat")


def test_rejects_a_word_that_needs_a_cell_twice() -> None:
    """Rejects a word that would have to turn back along its own line."""
    assert not exists([["a", "b"]], "aba")
    assert not exists(BOARD, "catac")


def test_does_not_wrap_around_the_edges() -> None:
    """Rejects a word that would run off one edge and continue from the other."""
    board = [
        ["a", "b", "c"],
        ["d", "e", "f"],
        ["g", "h", "i"],
    ]

    assert not exists(board, "bca")
    assert not exists(board, "cab")
    assert not exists(board, "gad")
    assert not exists(board, "hib")
    assert not exists(board, "afh")


def test_rejects_a_word_longer_than_any_line() -> None:
    """Rejects a word with more letters than the board is long."""
    assert not exists(BOARD, "catsx")
    assert not exists([["a", "a"], ["a", "a"]], "aaa")


def test_a_single_letter_is_found_wherever_it_is() -> None:
    """Finds a one-letter word at any cell and rejects a letter that is absent."""
    assert exists(BOARD, "g")
    assert exists(BOARD, "t")
    assert not exists(BOARD, "z")


def test_the_empty_word_is_always_present() -> None:
    """Returns True for the empty word, even in an empty grid."""
    assert exists(BOARD, "")
    assert exists([], "")
    assert exists([[]], "")


def test_an_empty_grid_holds_no_other_word() -> None:
    """Returns False for any non-empty word in a grid with no cells."""
    assert not exists([], "a")
    assert not exists([[]], "a")


def test_matching_is_exact() -> None:
    """Treats upper and lower case as different letters."""
    assert not exists(BOARD, "Cats")


def test_agrees_with_reading_every_line() -> None:
    """Matches a scan of every row, column and diagonal on every small board.

    Every 3 x 3 board over "ab" and every 2 x 4 board, against every word of
    one to four letters.
    """
    words = [
        "".join(letters)
        for size in range(1, 5)
        for letters in product("ab", repeat=size)
    ]
    for rows, columns in ((3, 3), (2, 4)):
        for cells in product("ab", repeat=rows * columns):
            board = [
                list(cells[row * columns : (row + 1) * columns]) for row in range(rows)
            ]
            for word in words:
                assert exists(board, word) == in_some_line(board, word), (board, word)


def test_leaves_the_board_alone() -> None:
    """Does not modify the board."""
    board = [["a", "b"], ["c", "d"]]

    exists(board, "ad")
    exists(board, "zz")

    assert board == [["a", "b"], ["c", "d"]]


def test_searches_a_large_board() -> None:
    """Searches a 50 x 50 board for a word that is only on one diagonal."""
    board = [["a"] * 50 for _ in range(50)]
    for index in range(10):
        board[20 + index][35 - index] = "b"

    assert exists(board, "b" * 10)
    assert not exists(board, "b" * 11)
    assert exists(board, "a" * 50)
