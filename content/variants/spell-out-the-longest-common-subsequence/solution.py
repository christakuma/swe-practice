"""Reference solution. CI asserts this passes every test in `tests.py`."""


def longest_common_subsequence(first: str, second: str) -> str:
    """Return a longest subsequence common to both strings.

    Two passes over one table. The first fills it exactly as the length-only
    version does: `table[i][j]` is the length for the first `i` characters of
    one string and the first `j` of the other.

    The second walks back from the far corner, undoing the decisions that
    produced each value. Where the two characters match, that match is part
    of an optimal answer -- keep the character and step diagonally. Where
    they differ, the cell copied its larger neighbour, so step to a neighbour
    with the same value.

    The whole table is kept. The one-row version of the fill overwrites the
    very cells the walk back needs to read.
    """
    rows, columns = len(first), len(second)
    table = [[0] * (columns + 1) for _ in range(rows + 1)]
    for i, a in enumerate(first, start=1):
        for j, b in enumerate(second, start=1):
            if a == b:
                table[i][j] = table[i - 1][j - 1] + 1
            else:
                table[i][j] = max(table[i - 1][j], table[i][j - 1])

    kept: list[str] = []
    i, j = rows, columns
    while i > 0 and j > 0:
        if first[i - 1] == second[j - 1]:
            kept.append(first[i - 1])
            i -= 1
            j -= 1
        elif table[i - 1][j] >= table[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return "".join(reversed(kept))
