# Longest Common Subsequence — two cases, and the diagonal

Revealed after grading. The problem is the classic one (LeetCode 1143); the
wording above is ours. It is the canonical two-dimensional DP, and the two
things worth taking from it are the **mismatch case** (which distinguishes it
from a problem it is easily confused with) and the **diagonal dependency**
(which is what makes collapsing the table tricky).

## The recurrence

Compare one character from each string. Two cases, exhaustively:

- **They match.** That character can be used, and the rest of the problem is
  both strings without it: `1 + diagonal`.
- **They do not match.** At least one is unusable and you do not know which,
  so try dropping each: `max(left, above)`.

Empty prefixes give zero. `O(m·n)` cells, each `O(1)`.

## Subsequence, not substring

The mismatch case is the whole difference:

| | on a mismatch |
|---|---|
| longest common **subsequence** | `max(left, above)` — carry the best forward |
| longest common **substring** | `0` — the run is broken |

Subsequences may skip characters; substrings may not. Two problems with nearly
identical tables and genuinely different recurrences, which is worth knowing
*before* reaching for a half-remembered one.
`test_is_not_a_substring_search` uses `"abcde"` against `"ace"`: the substring
answer is 1, the subsequence answer is 3.

## Why order matters and counting does not

```python
lcs_length("abc", "cba") == 1
```

Both strings hold the same three characters. A solution that counts shared
characters — a multiset intersection — reports 3. The table gets it right
because the recurrence only ever extends a match by looking *backwards* in both
strings at once, which is what encodes "in the same order".

## Collapsing to one row, and the trap

The recurrence reaches back one row, so one row should suffice. The problem:
the **match** case needs the *diagonal* — the previous row's value at
`index - 1` — and a left-to-right sweep has already overwritten it.

```python
for outer in first:
    previous_diagonal = 0
    for index, inner in enumerate(second, start=1):
        overwritten = row[index]              # this is next column's diagonal
        if outer == inner:
            row[index] = previous_diagonal + 1
        else:
            row[index] = max(row[index], row[index - 1])
        previous_diagonal = overwritten
```

One scalar, saved one step before it is clobbered.

**This is the standard hazard when rolling up a 2-D table, and it is worth
stating as a rule: check which neighbours the recurrence needs before deciding
how many rows to keep.** A recurrence needing only `above` and `left` (like
[count paths through a grid](../count-paths-through-a-grid/notes.md)) collapses
to one row with no extra state. One that also needs `diagonal` needs one more
scalar. One that needs two rows back needs two rows.

Keeping two full rows is clearer and costs the same `O(min(m, n))`. The scalar
version is written out here because the diagonal is specifically what people
get wrong when they try this, and naming it is the fix.

## Symmetry is free, and worth asserting

"Common" is symmetric, so the answer cannot depend on argument order. Swapping
the strings to keep the shorter one along the row is therefore safe — and
`test_is_symmetric` is there because that swap is also where an inconsistent
index creeps in.

**A symmetry in the problem is a free test.** Same category as the involutions
in [rotate a matrix](../rotate-a-matrix-in-place/notes.md) and
[invert a binary tree](../invert-a-binary-tree/notes.md): a property that holds
for all inputs, requiring no expected values.

## What to take away

The recurrence is two lines and most people can reproduce it. The transferable
parts are smaller and easier to get wrong:

**Name the neighbours your recurrence reads.** It determines the space
reduction, and it is the difference between a correct roll-up and a subtle one.

**Check which problem you are solving.** Subsequence and substring differ in
one branch. "I remember this table" is the most expensive kind of recall.
