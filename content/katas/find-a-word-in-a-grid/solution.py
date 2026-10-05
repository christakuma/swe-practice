"""Reference solution. CI asserts this passes every test in `tests.py`."""

VISITED = "\x00"  # a sentinel no real board cell can hold


def exists(board: list[list[str]], word: str) -> bool:
    """Return whether `word` can be spelled along a path through `board`.

    Depth-first search whose state is a pair: where you are in the grid and how
    far through the word you are. A cell succeeds if its letter matches and
    *some* neighbour can spell the rest -- so the four recursive calls are
    combined with `or`, and Python's short-circuiting means the first branch
    that works stops the search.

    **The unmarking is the kata.** The no-reuse rule applies to the current
    path, not to the search as a whole: a cell that leads nowhere from here may
    be exactly what another path needs. A permanent `visited` set is therefore
    wrong -- it makes the search depend on the order starting cells happen to
    be tried, and it reports False for words that are present.

    So the mark has the lifetime of the path. Writing a sentinel into the board
    and restoring the letter on the way out gives that for free and needs no
    second structure; `board[r][c] = letter` in the unwind is what turns a
    plain DFS into *backtracking*.

    Mutating the caller's board and putting it back is a deliberate trade and
    worth being uneasy about: it is O(1) extra space rather than O(L), and the
    grid is identical by the time the function returns -- but it is not
    reentrant, and it would be visible to another thread mid-search. The
    alternative, a `set` of coordinates added before the recursion and
    discarded after, is the same algorithm and the better default in real code.

    The length check is not an optimisation. A word longer than the grid cannot
    fit, and bailing early keeps the worst case from being explored at all.
    """
    if not word:
        return True
    if not board or not board[0]:
        return False

    rows, columns = len(board), len(board[0])
    if len(word) > rows * columns:
        return False

    def search(row: int, column: int, index: int) -> bool:
        if index == len(word):
            return True
        if not (0 <= row < rows and 0 <= column < columns):
            return False
        letter = board[row][column]
        if letter != word[index]:
            return False

        board[row][column] = VISITED
        found = (
            search(row + 1, column, index + 1)
            or search(row - 1, column, index + 1)
            or search(row, column + 1, index + 1)
            or search(row, column - 1, index + 1)
        )
        board[row][column] = letter
        return found

    return any(
        search(row, column, 0) for row in range(rows) for column in range(columns)
    )
