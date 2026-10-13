# A search with one decision in it is a loop

Revealed after grading. This is the word search printed in newspapers.

The standard problem is hard for a reason that is easy to lose sight of: at
every letter the path chooses again. That is what creates the exponential
search, the backtracking, and the need to mark cells as used.

A straight line makes **one** choice — the direction — and makes it at the
start. After that every cell is determined:

```python
board[row + index * row_step][column + index * column_step]
```

No recursion, no visited set, nothing to undo. Every start, every direction,
read along. The "uses no cell twice" rule from the standard version comes for
free: a straight line cannot return to a cell.

## The two ways to get it wrong

**Keeping the old search.** The standard solution, even extended to
diagonals, accepts bent paths. `c a` over `· t` spells "cat" round a corner.

**Trusting Python's indexing.** Stepping up from row 0 gives row -1, and
`board[-1]` is a perfectly good row — the last one. With no bounds check, the
word wraps round the board like a torus: `"bca"` is found in the row
`a b c`. An `IndexError` only protects one side of each axis.

Check where the *last* letter lands before reading anything. Both ends on the
board means the whole line is.

## What the twist was testing

Whether the difficulty of the standard problem was located correctly. It is
tempting to file "word in a grid" under backtracking. The backtracking comes
from the freedom to turn; remove the freedom and it is a triple loop. Many
"harder-looking" follow-ups are easier than what they follow, and reaching
for the heavy tool anyway is the mistake.
