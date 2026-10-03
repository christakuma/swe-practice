"""Reference solution. CI asserts this passes every test in `tests.py`."""


def edit_distance(source: str, target: str) -> int:
    """Return the fewest single-character edits that turn one string into other.

    Levenshtein distance. `distance[i][j]` is the answer for the first i
    characters of `source` and the first j of `target`, and the recurrence comes
    from asking what the last edit was -- there are only four possibilities:

    * the two characters already match, so nothing was spent: `distance[i-1][j-1]`
    * a replacement:                                      1 + `distance[i-1][j-1]`
    * a deletion from source:                             1 + `distance[i-1][j]`
    * an insertion into source:                           1 + `distance[i][j-1]`

    The base cases are the whole of the edge-case handling: turning an empty
    string into j characters costs j insertions, and i characters into nothing
    costs i deletions. Both rows are filled before the loop, which is why there
    is no special case for an empty input anywhere in the body.

    Two rows rather than the full table, because the recurrence reaches back one
    row only. That takes the space from O(n*m) to O(m) and is the reason this is
    usable on long strings -- and it is also what makes recovering the *edits*
    impossible, since the path through the table is gone. Keeping the table is
    the price of an answer you can show someone.
    """
    previous = list(range(len(target) + 1))
    for row, source_character in enumerate(source, start=1):
        current = [row] + [0] * len(target)
        for column, target_character in enumerate(target, start=1):
            if source_character == target_character:
                current[column] = previous[column - 1]
            else:
                current[column] = 1 + min(
                    previous[column - 1],  # replace
                    previous[column],  # delete
                    current[column - 1],  # insert
                )
        previous = current
    return previous[len(target)]
