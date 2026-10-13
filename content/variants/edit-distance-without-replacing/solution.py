"""Reference solution. CI asserts this passes every test in `tests.py`."""


def edit_distance(source: str, target: str) -> int:
    """Return the fewest insertions and deletions turning `source` into `target`.

    The standard table with one move taken out. Cell `(i, j)` is still the
    distance between two prefixes, and the borders are still "delete
    everything" and "insert everything". Inside:

    - if the two characters match, nothing needs doing: take the diagonal;
    - if they differ, there is no replace to pay for. One of the two
      characters has to go -- delete from `source` or insert into `target`.

    One row is kept. `diagonal` carries the value that `row[column]` held
    before it was overwritten, which is the cell up and to the left.
    """
    row = list(range(len(target) + 1))
    for deleted, source_character in enumerate(source, start=1):
        diagonal, row[0] = row[0], deleted
        for column, target_character in enumerate(target, start=1):
            above = row[column]
            if source_character == target_character:
                row[column] = diagonal
            else:
                row[column] = 1 + min(above, row[column - 1])
            diagonal = above
    return row[-1]
