"""Reference solution. CI asserts this passes every test in `tests.py`."""


def lcs_length(first: str, second: str) -> int:
    """Return the length of the longest common subsequence.

    Compare one character from each string and there are exactly two cases:

    - **they match** -- that character can be part of the answer, and the rest
      of the problem is both strings without it, so `1 + diagonal`;
    - **they do not match** -- at least one of them is unusable, and you do not
      know which, so try dropping each and take the better: `max(left, above)`.

    An empty prefix has a common subsequence of length zero, which is the base
    case along two edges of the table.

    Note that the mismatch case is where this differs from the longest common
    *substring*, which would reset to zero instead of carrying the better
    answer forward -- subsequences may skip characters, substrings may not. The
    two problems have nearly identical tables and genuinely different
    recurrences, which is worth knowing before reaching for a half-remembered
    one.

    **One row plus one scalar.** The recurrence reaches back one row, so a
    single row suffices -- except that the `match` case needs the *diagonal*,
    which is the previous row's value at `index - 1`, and the sweep has already
    overwritten it. `previous_diagonal` is that value, saved one step before it
    is clobbered. Keeping two full rows is the clearer version and costs
    O(min(m, n)) either way; the scalar is here because the diagonal dependency
    is the thing people get wrong when they try to collapse this table, and
    naming it is the fix.

    Iterating the shorter string along the row keeps the stored row small. The
    answer is symmetric, since "common" is.
    """
    if not first or not second:
        return 0

    if len(first) < len(second):
        first, second = second, first

    row = [0] * (len(second) + 1)
    for outer in first:
        previous_diagonal = 0
        for index, inner in enumerate(second, start=1):
            # Save the value about to be overwritten: it is the diagonal for
            # the *next* column.
            overwritten = row[index]
            if outer == inner:
                row[index] = previous_diagonal + 1
            else:
                row[index] = max(row[index], row[index - 1])
            previous_diagonal = overwritten

    return row[-1]
