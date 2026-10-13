"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import find_words


def spelled(board: list[list[str]], word: str) -> bool:
    """Whether one word can be walked on the wrapped board. An oracle.

    It searches for a single word with a set of used cells, and shares
    nothing with a trie.
    """
    rows, columns = len(board), len(board[0])

    def walk(
        row: int, column: int, index: int, used: frozenset[tuple[int, int]]
    ) -> bool:
        if board[row][column] != word[index] or (row, column) in used:
            return False
        if index == len(word) - 1:
            return True
        used = used | {(row, column)}
        return any(
            walk((row + down) % rows, (column + right) % columns, index + 1, used)
            for down, right in ((1, 0), (-1, 0), (0, 1), (0, -1))
        )

    return any(
        walk(row, column, 0, frozenset())
        for row in range(rows)
        for column in range(columns)
    )


def test_steps_off_the_right_edge_onto_the_left() -> None:
    """Finds a word that leaves by the last column and arrives at the first."""
    assert find_words([["a", "b", "c"]], ["ca"]) == ["ca"]


def test_steps_off_the_left_edge_onto_the_right() -> None:
    """Finds a word that leaves by the first column and arrives at the last."""
    assert find_words([["a", "b", "c"]], ["ac"]) == ["ac"]


def test_steps_off_the_bottom_and_the_top() -> None:
    """Finds words that wrap vertically in either direction."""
    board = [["a"], ["b"], ["c"]]

    assert find_words(board, ["ca", "ac"]) == ["ac", "ca"]


def test_a_path_may_wrap_both_ways() -> None:
    """Finds a word whose path wraps across a column edge and then a row edge."""
    board = [
        ["a", "x", "b"],
        ["y", "z", "w"],
        ["q", "v", "c"],
    ]

    assert find_words(board, ["abc"]) == ["abc"]


def test_wrapping_adds_no_diagonals() -> None:
    """Refuses a word that would need a diagonal step, wrapped or not."""
    board = [
        ["a", "x", "p"],
        ["y", "b", "q"],
        ["r", "s", "c"],
    ]

    assert find_words(board, ["ab", "ac", "bc"]) == []


def test_still_finds_words_that_do_not_wrap() -> None:
    """Finds ordinary paths through the middle of the grid."""
    board = [
        ["o", "a", "a", "n"],
        ["e", "t", "a", "e"],
        ["i", "h", "k", "r"],
        ["i", "f", "l", "v"],
    ]

    assert find_words(board, ["oath", "eat", "pea"]) == ["eat", "oath"]


def test_one_column_has_no_sideways_step() -> None:
    """Refuses to reuse a cell reached by stepping sideways off a single column.

    Left and right of each cell is that cell. "aa" is there going down;
    "aaa" would need a third a.
    """
    board = [["a"], ["a"]]

    assert find_words(board, ["a", "aa", "aaa"]) == ["a", "aa"]
    assert find_words([["a"], ["b"], ["c"]], ["ab", "aab"]) == ["ab"]


def test_a_single_cell_is_its_own_neighbour_and_cannot_be_reused() -> None:
    """Finds only the one-letter word on a one-by-one grid."""
    assert find_words([["a"]], ["a", "aa"]) == ["a"]


def test_two_columns_do_not_make_two_neighbours() -> None:
    """Counts the cell to the left and the cell to the right as one cell."""
    assert find_words([["a", "b"]], ["ab", "ba", "aba", "bab"]) == ["ab", "ba"]


def test_cannot_walk_round_the_grid_through_its_own_start() -> None:
    """Refuses a path that goes all the way round a row and uses a cell again.

    The top row is three cells in a ring. "abca" goes right three times and
    arrives where it began -- and it is shorter than the grid has cells, so
    counting letters does not rule it out.
    """
    board = [["a", "b", "c"], ["x", "y", "z"]]

    assert find_words(board, ["abc", "abca", "cabc"]) == ["abc"]
    assert find_words([["a", "b", "c"]], ["abc", "abca"]) == ["abc"]


def test_returns_each_word_once_and_sorted() -> None:
    """Returns a word once however often it is listed or however many paths spell it."""
    board = [["a", "b"], ["b", "a"]]

    assert find_words(board, ["ba", "ab", "ab", "ba"]) == ["ab", "ba"]


def test_ignores_the_empty_word_and_words_too_long_for_the_grid() -> None:
    """Never returns the empty string or a word with more letters than cells."""
    assert find_words([["a", "a"]], ["", "a", "aa", "aaa"]) == ["a", "aa"]


def test_handles_an_empty_board_and_an_empty_word_list() -> None:
    """Returns an empty list when there is nothing to search or nothing to find."""
    assert find_words([], ["a"]) == []
    assert find_words([[]], ["a"]) == []
    assert find_words([["a"]], []) == []


def test_restores_the_board() -> None:
    """Leaves every cell holding what it held."""
    board = [["a", "b", "c"], ["d", "e", "f"]]

    find_words(board, ["abc", "cad", "fda", "zzz"])

    assert board == [["a", "b", "c"], ["d", "e", "f"]]


def test_agrees_with_a_per_word_search_on_every_small_board() -> None:
    """Matches a word-at-a-time search on every two-letter board up to 2 x 3.

    Every board of each shape, and every word of up to five letters over the
    same two letters. The narrow shapes are in there on purpose.
    """
    words = [
        "".join(letters)
        for size in range(1, 6)
        for letters in product("ab", repeat=size)
    ]
    for rows, columns in (
        (1, 1),
        (1, 2),
        (2, 1),
        (1, 3),
        (3, 1),
        (2, 2),
        (2, 3),
        (3, 2),
    ):
        for cells in product("ab", repeat=rows * columns):
            board = [
                list(cells[row * columns : (row + 1) * columns]) for row in range(rows)
            ]
            expected = sorted(word for word in words if spelled(board, word))

            assert find_words(board, words) == expected, board


def test_agrees_with_a_per_word_search_on_three_by_three_boards() -> None:
    """Matches a word-at-a-time search on a spread of 3 x 3 boards."""
    words = [
        "".join(letters)
        for size in range(1, 5)
        for letters in product("ab", repeat=size)
    ]
    for number, cells in enumerate(product("ab", repeat=9)):
        if number % 7:
            continue
        board = [list(cells[row * 3 : row * 3 + 3]) for row in range(3)]
        expected = sorted(word for word in words if spelled(board, word))

        assert find_words(board, words) == expected, board


def test_finds_many_words_on_the_largest_grid() -> None:
    """Searches a 6 x 6 grid for a hundred words, most of them sharing prefixes."""
    board = [
        [chr(ord("a") + (3 * row + 5 * column) % 7) for column in range(6)]
        for row in range(6)
    ]
    stems = ["".join(letters) for letters in product("abcdefg", repeat=2)]
    words = [stem + tail for stem in stems for tail in ("da", "fb")][:100]
    expected = sorted(word for word in words if spelled(board, word))

    assert len(expected) > 5
    assert find_words(board, words) == expected
