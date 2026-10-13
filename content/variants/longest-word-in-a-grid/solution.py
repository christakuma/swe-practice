"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_word(board: list[list[str]], words: list[str]) -> str:
    """Return the longest word from `words` that can be spelled in `board`.

    The words are tried in the order the answer is ranked in -- longest
    first, then alphabetically -- so the first one found is the answer and
    the search stops there. That ordering is the whole difference from
    listing every word, where nothing can be skipped.
    """

    def spelled(word: str) -> bool:
        def search(y: int, x: int, at: int) -> bool:
            if not (0 <= y < len(board) and 0 <= x < len(board[y])):
                return False
            if board[y][x] != word[at]:
                return False
            if at == len(word) - 1:
                return True
            board[y][x] = ""
            found = (
                search(y + 1, x, at + 1)
                or search(y - 1, x, at + 1)
                or search(y, x + 1, at + 1)
                or search(y, x - 1, at + 1)
            )
            board[y][x] = word[at]
            return found

        return any(
            search(y, x, 0) for y in range(len(board)) for x in range(len(board[y]))
        )

    for word in sorted({word for word in words if word}, key=lambda w: (-len(w), w)):
        if spelled(word):
            return word
    return ""
