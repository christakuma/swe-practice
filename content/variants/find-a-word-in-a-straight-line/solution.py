"""Reference solution. CI asserts this passes every test in `tests.py`."""

DIRECTIONS = [
    (row_step, column_step)
    for row_step in (-1, 0, 1)
    for column_step in (-1, 0, 1)
    if (row_step, column_step) != (0, 0)
]


def exists(board: list[list[str]], word: str) -> bool:
    """Return whether `word` lies in a straight line somewhere in `board`.

    A straight path is fixed by where it starts and which way it heads, so
    there is nothing to search: for every cell and every direction, read
    `len(word)` cells along the line and compare.

    The bounds are checked for the last letter only, which is enough -- the
    line is straight, so if both ends are on the board everything between
    them is. They do have to be checked explicitly: an index of -1 is legal
    Python and would read the far edge, wrapping the word round the board.
    """
    if not word:
        return True
    rows = len(board)
    columns = len(board[0]) if board else 0
    reach = len(word) - 1
    for row in range(rows):
        for column in range(columns):
            for row_step, column_step in DIRECTIONS:
                last_row = row + reach * row_step
                last_column = column + reach * column_step
                if not (0 <= last_row < rows and 0 <= last_column < columns):
                    continue
                if all(
                    board[row + index * row_step][column + index * column_step]
                    == letter
                    for index, letter in enumerate(word)
                ):
                    return True
    return False
