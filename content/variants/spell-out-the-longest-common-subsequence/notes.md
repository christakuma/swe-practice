# The table already knows; you have to ask it

Revealed after grading. LeetCode's version of this asks you to print the
"Shortest Common Supersequence" (1092), which is the same walk.

The length-only solution fills a table and reads one number from its corner.
Every other cell is thrown away — literally, in the one-row version. This
problem is those other cells.

Each cell got its value in one of two ways:

- its characters matched: `1 + diagonal`;
- they did not: a copy of the larger of *above* and *left*.

So the table is a record of decisions, and the answer is recovered by
replaying them backwards from the corner:

```python
while i > 0 and j > 0:
    if first[i - 1] == second[j - 1]:
        kept.append(first[i - 1]); i -= 1; j -= 1
    elif table[i - 1][j] >= table[i][j - 1]:
        i -= 1
    else:
        j -= 1
```

Characters arrive last-first, so reverse at the end.

## Why not just match greedily?

Scanning `first` and taking each character's earliest remaining match in
`second` produces *a* common subsequence, not the longest. In
`"axbcd"` / `"bcda"`, the `a` matches at the very end of the second string
and nothing after it can match at all; the answer, `"bcd"`, skips the `a`.
Which matches to skip is precisely the knowledge the table holds.

## The space trade

The standard problem rewards cutting the table to one row. Do that here and
the walk back has nothing to walk through. `O(m * n)` memory is the price of
the string. (Hirschberg's algorithm gets it back to linear by divide and
conquer, and is the right answer to "now do it for two files of a million
lines each" — which is what `diff` does.)

## What the twist was testing

"Return the thing, not its size" is the most common follow-up to any dynamic
programming answer. It is never a new algorithm. It is always: keep the
table, and walk back through the choices. Being able to say that — and to
say what it costs — matters more than this particular walk.
