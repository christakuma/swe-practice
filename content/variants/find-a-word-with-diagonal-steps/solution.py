"""Reference solution. CI asserts this passes every test in `tests.py`."""


def exists(board: list[list[str]], word: str) -> bool:
    """Return whether `word` can be spelled along a path of 8-way steps.

    Depth-first search with the cell blanked while it is on the current path
    and restored on the way out. The restore is in a `finally`-shaped place:
    after the loop, on every path out of the call, so the board is intact
    whether the search succeeds or fails.
    """
    if not word:
        return True

    def search(y: int, x: int, at: int) -> bool:
        if not (0 <= y < len(board) and 0 <= x < len(board[y])):
            return False
        if board[y][x] != word[at]:
            return False
        if at == len(word) - 1:
            return True
        board[y][x] = ""
        found = any(
            search(y + dy, x + dx, at + 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
        )
        board[y][x] = word[at]
        return found

    return any(search(y, x, 0) for y in range(len(board)) for x in range(len(board[y])))
