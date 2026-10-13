# Remove one move and the table tells you what it was for

Revealed after grading. This is "Delete Operation for Two Strings"
(LeetCode 583).

The standard table has three ways into a cell: from above (delete), from the
left (insert), and from the diagonal — free if the characters match, one edit
if they differ. This version removes the paid diagonal and keeps the free
one:

```python
if source_character == target_character:
    row[column] = diagonal
else:
    row[column] = 1 + min(above, row[column - 1])
```

Two ways to get the edit wrong, in opposite directions:

- **Keep the diagonal at cost 1.** That is the standard solution, and
  `"cat" -> "cut"` comes out as 1.
- **Remove the diagonal altogether.** Then matching characters are deleted and
  re-inserted, and identical strings have a distance of twice their length.

## It is the longest common subsequence in disguise

With only insertions and deletions, every character of `source` is either
deleted or kept, and every character of `target` is either inserted or was
kept. The kept characters appear in both strings in the same order — a common
subsequence. Keeping more means editing less, so:

```
distance = len(source) + len(target) - 2 * LCS(source, target)
```

That is how the tests check the answer. If you solved the LCS kata, this
problem was one line on top of it. The standard edit distance has no such
shortcut; replace is what makes it its own problem.

## What the twist was testing

Whether the three moves in the table were understood as three *operations*,
each of which can be priced or removed independently. Weighted edits, a
transposition move, a free substitution between similar letters — all of them
are edits to the same handful of lines, provided you know which line is which
operation.
