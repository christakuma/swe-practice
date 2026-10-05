"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import exists

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))

BOARD = [
    ["A", "B", "C", "E"],
    ["S", "F", "C", "S"],
    ["A", "D", "E", "E"],
]


def reference(board: list[list[str]], word: str) -> bool:
    """Search with an immutable set of used cells -- an independent oracle.

    It never writes to the board, so it shares no state management with a
    mark-and-restore implementation. Exponential and fine at these sizes.
    """
    if not word:
        return True
    if not board or not board[0]:
        return False
    rows, columns = len(board), len(board[0])

    def walk(
        row: int, column: int, index: int, used: frozenset[tuple[int, int]]
    ) -> bool:
        if not (0 <= row < rows and 0 <= column < columns):
            return False
        if (row, column) in used or board[row][column] != word[index]:
            return False
        if index == len(word) - 1:
            return True
        ahead = used | {(row, column)}
        return any(walk(row + dr, column + dc, index + 1, ahead) for dr, dc in STEPS)

    return any(
        walk(row, column, 0, frozenset())
        for row in range(rows)
        for column in range(columns)
    )


def fresh() -> list[list[str]]:
    """A copy of the worked-example board."""
    return [list(row) for row in BOARD]


def test_finds_a_winding_word() -> None:
    """Finds a word whose path turns corners."""
    assert exists(fresh(), "ABCCED") is True


def test_finds_a_short_word() -> None:
    """Finds a word that runs backwards along a row and up a column."""
    assert exists(fresh(), "SEE") is True


def test_refuses_to_reuse_a_cell() -> None:
    """Rejects a word that would need the same cell twice.

    Every letter of ABCB is on the board and the path is forced to step back
    onto the B it came from. A search without per-path marking returns True.
    """
    assert exists(fresh(), "ABCB") is False


def test_accepts_the_empty_word() -> None:
    """Reports the empty word as present."""
    assert exists(fresh(), "") is True
    assert exists([], "") is True


def test_handles_an_empty_board() -> None:
    """Rejects a non-empty word on an empty board."""
    assert exists([], "A") is False
    assert exists([[]], "A") is False


def test_finds_a_single_letter() -> None:
    """Finds a one-letter word, and rejects a letter that is absent."""
    assert exists(fresh(), "A") is True
    assert exists(fresh(), "Z") is False


def test_rejects_a_word_longer_than_the_board() -> None:
    """Rejects a word with more letters than the grid has cells."""
    assert exists([["A", "A"], ["A", "A"]], "AAAAA") is False


def test_refuses_diagonal_steps() -> None:
    """Rejects a word that would need a diagonal move.

    On this board AD are diagonal neighbours and share no orthogonal path.
    """
    assert exists([["A", "B"], ["C", "D"]], "AD") is False
    assert exists([["A", "B"], ["C", "D"]], "AB") is True


def test_uses_a_cell_freed_by_backtracking() -> None:
    """Finds a word that needs a cell an earlier failed path stepped on.

    The smallest grid that separates backtracking from a permanent visited
    set. The only path is (1,0) -> (0,0) -> (0,1) -> (1,1), so every A must
    stay available after the dead ends that touch it: starting at (0,0) and
    walking to (0,1) strands the search, and a visited set that is never
    discarded leaves those cells spent, so the real path is never tried.
    Verified against that bug rather than assumed -- it returns False here and
    passes every other test in this file.
    """
    board = [["A", "A"], ["A", "B"]]

    assert exists(board, "AAAB") is True


def test_restores_the_board() -> None:
    """Leaves the board as it found it, on success and on failure.

    Marking cells by writing into the grid is allowed; leaving the sentinel
    behind is not -- the caller still owns that data.
    """
    board = fresh()

    exists(board, "ABCCED")
    assert board == BOARD

    exists(board, "ZZZZZZ")
    assert board == BOARD


def test_agrees_with_a_reference_across_every_small_grid_and_word() -> None:
    """Matches the oracle for every 2x2 and 2x3 grid over {A, B} and short words.

    Enumerating the grids rather than choosing them is what makes this
    convincing: the reuse bug and the permanent-marking bug each need a
    particular arrangement of repeated letters, and guessing which arrangement
    is harder than trying all of them.
    """
    words = [
        "A",
        "B",
        "AA",
        "AB",
        "BA",
        "BB",
        "AAA",
        "ABA",
        "AAB",
        "AAAB",
        "ABAB",
        "AABB",
    ]
    for rows, columns in ((2, 2), (2, 3)):
        for letters in product("AB", repeat=rows * columns):
            grid = [
                list(letters[row * columns : (row + 1) * columns])
                for row in range(rows)
            ]
            for word in words:
                board = [list(row) for row in grid]
                expected = reference(grid, word)

                assert exists(board, word) is expected, (letters, word)


def test_searches_a_large_uniform_board_within_the_time_limit() -> None:
    """Rejects an absent word on a board of identical letters.

    The pathological input: every cell matches every letter, so the search
    explores a vast number of paths before concluding. The final Z is nowhere,
    which is what makes it search rather than succeed early.
    """
    board = [["A"] * 8 for _ in range(8)]

    assert exists(board, "AAAAAAAAAAZ") is False
