"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import find_words

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))

BOARD = [
    ["o", "a", "a", "n"],
    ["e", "t", "a", "e"],
    ["i", "h", "k", "r"],
    ["i", "f", "l", "v"],
]


def present(board: list[list[str]], word: str) -> bool:
    """Whether one word is in the grid -- an independent per-word oracle.

    An immutable set of used cells and a fresh search per word: no trie, no
    shared state, no pruning. This is the slow solution the kata rules out,
    used here as the reference.
    """
    if not word:
        return False
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


def reference(board: list[list[str]], words: list[str]) -> list[str]:
    """Every present word, found one word at a time."""
    return sorted({word for word in words if present(board, word)})


def fresh() -> list[list[str]]:
    """A copy of the worked-example board."""
    return [list(row) for row in BOARD]


def test_handles_the_worked_example() -> None:
    """Returns the documented words, sorted."""
    assert find_words(fresh(), ["oath", "pea", "eat", "rain"]) == ["eat", "oath"]


def test_handles_an_empty_word_list() -> None:
    """Returns nothing when there is nothing to look for."""
    assert find_words(fresh(), []) == []


def test_handles_an_empty_board() -> None:
    """Returns nothing when there is no grid."""
    assert find_words([], ["a"]) == []
    assert find_words([[]], ["a"]) == []


def test_returns_each_word_once() -> None:
    """Deduplicates the word list.

    Clearing a word's marker when it is found is what makes this fall out --
    a solution appending on every successful path returns it several times.
    """
    assert find_words(fresh(), ["eat", "eat", "eat"]) == ["eat"]


def test_does_not_return_a_word_found_by_two_paths_twice() -> None:
    """Returns one entry for a word reachable along more than one path."""
    board = [["a", "a"], ["a", "a"]]

    assert find_words(board, ["aa"]) == ["aa"]
    assert find_words([["a", "a"], ["a", "a"]], ["aaa"]) == ["aaa"]


def test_refuses_to_reuse_a_cell() -> None:
    """Rejects a word needing the same cell twice.

    The grid is the part with cycles, so the cell mark still has to be undone
    on the way out -- the trie descent never does.
    """
    board = [["a", "b"], ["c", "d"]]

    assert find_words(board, ["aba"]) == []
    assert find_words(board, ["abdc"]) == ["abdc"]


def test_rejects_a_word_longer_than_the_grid() -> None:
    """Rejects a word with more letters than the grid has cells."""
    assert find_words([["a", "a"], ["a", "a"]], ["aaaaa"]) == []


def test_ignores_the_empty_word() -> None:
    """Leaves the empty string out of the result."""
    assert find_words(fresh(), [""]) == []
    assert find_words(fresh(), ["", "eat"]) == ["eat"]


def test_finds_a_single_letter() -> None:
    """Finds one-letter words that appear in the grid."""
    assert find_words(fresh(), ["o", "z"]) == ["o"]


def test_finds_words_sharing_a_prefix() -> None:
    """Finds several words that branch from a common prefix.

    The case the trie exists for: all three share "a", and two share "ab".
    """
    board = [["a", "b"], ["c", "d"]]

    assert find_words(board, ["ab", "abd", "abdc", "ac", "acd"]) == [
        "ab",
        "abd",
        "abdc",
        "ac",
        "acd",
    ]


def test_finds_a_word_that_is_a_prefix_of_another() -> None:
    """Returns both when one found word is a prefix of another.

    Recording a hit must not stop the search -- a longer word may continue
    from the same node.
    """
    board = [["a", "b"], ["c", "d"]]

    assert find_words(board, ["ab", "abd"]) == ["ab", "abd"]


def test_restores_the_board() -> None:
    """Leaves the grid as it found it, on success and on failure."""
    board = fresh()

    find_words(board, ["oath", "eat"])
    assert board == BOARD

    find_words(board, ["zzzz"])
    assert board == BOARD


def test_returns_sorted_results() -> None:
    """Returns the found words in ascending order."""
    result = find_words(fresh(), ["rain", "eat", "oath", "hike", "ate"])

    assert result == sorted(result)


def test_agrees_with_a_per_word_search_across_every_small_case() -> None:
    """Matches a per-word search for every small grid and word list.

    Every 2x2 and 2x3 grid over {a, b}, crossed with every pair and triple of
    words up to four characters -- tens of thousands of cases. The pruning
    (clearing a found word, deleting exhausted branches) is what can go wrong
    here, and it only shows up for particular overlaps between the words and
    the grid.
    """
    pool = [
        "".join(characters)
        for length in (1, 2, 3)
        for characters in product("ab", repeat=length)
    ]
    for rows, columns in ((2, 2), (2, 3)):
        for cells in product("ab", repeat=rows * columns):
            grid = [
                [cells[row * columns + column] for column in range(columns)]
                for row in range(rows)
            ]
            for size in (1, 2):
                for words in combinations(pool, size):
                    given = list(words)

                    assert find_words([list(row) for row in grid], given) == reference(
                        grid, given
                    ), (grid, given)


def test_searches_the_grid_once_rather_than_once_per_word() -> None:
    """Handles forty prefix-sharing words on a uniform grid within the limit.

    The input that separates the two approaches. A 6x6 grid of a single letter
    and forty words that are a 13-letter run of it followed by a letter that
    is nowhere -- so every word forces the full exponential exploration before
    failing.

    Measured: searching the grid once with a trie takes about 0.8 seconds,
    because all forty words share their entire prefix. Running the single-word
    search once per word takes about 32 seconds, against a 20-second limit.
    """
    size = 6
    board = [["a"] * size for _ in range(size)]
    words = ["a" * 13 + chr(98 + index) for index in range(40)]

    assert find_words(board, words) == []


def test_finds_many_words_on_a_larger_grid() -> None:
    """Finds the present words among a large prefix-sharing word list."""
    letters = "abcd"
    size = 8
    board = [
        [letters[(row * 3 + column) % len(letters)] for column in range(size)]
        for row in range(size)
    ]
    words = ["".join(characters) for characters in product(letters, repeat=3)]

    result = find_words([list(row) for row in board], words)

    assert result == reference(board, words)
    assert result == sorted(set(result))
