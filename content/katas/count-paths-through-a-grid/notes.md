# Count Paths Through a Grid — one row, overwritten in place

Revealed after grading. The problem is the classic one (LeetCode 62); the
wording above is ours. The recurrence is the easiest in the library; the reason
to do it is the space reduction, which is one line and is the single most
reusable trick in tabular dynamic programming.

## The recurrence

You can only arrive at a cell from **above** or from the **left**, so:

```
ways(r, c) = ways(r - 1, c) + ways(r, c - 1)
```

with the top row and left column at 1 each — one way along an edge.

Filling row by row makes every dependency already final: the cell above is in
the previous row, the cell to the left is earlier in this one. Same argument as
[count bits for every number up to n](../count-bits-for-every-number-up-to-n/notes.md):
**dynamic programming is an ordering in which the subproblems you need are
behind you.**

## The line worth understanding

```python
row = [1] * short
for _ in range(long - 1):
    for column in range(1, short):
        row[column] += row[column - 1]
```

One array, `O(min(m, n))` space instead of `O(m·n)`. Why it works:

- Before the assignment, `row[column]` still holds the **previous row's** value
  for this column — which is the cell *above*.
- `row[column - 1]` has already been updated this pass — which is the cell to
  the *left*.

Both operands mean the right thing at the moment they are read, so the `+=`
is literally the recurrence. The direction is load-bearing: iterate right to
left and `row[column - 1]` is still the old row, which is the wrong neighbour.

**The general rule: a table whose recurrence only reaches back one row needs
only one row.** The direction of the sweep then determines whether an entry is
"this row" or "last row" at the moment you touch it, and getting that backwards
is the standard bug. It is the same reasoning behind the rolling two-variable
form of [climbing stairs](../climbing-stairs/notes.md) and the single-array
knapsack.

## Keep the shorter dimension

The answer is symmetric — a path is a sequence of moves and swapping the axes
just relabels them — so storing `min(width, height)` is free.
`test_handles_a_long_thin_grid` uses a 100,000 × 2 grid, where storing the long
dimension is a hundred thousand entries for no reason.

`test_is_symmetric` checks it across 196 size pairs, which is also the test
that catches picking the shorter dimension and then indexing it with the longer
one.

## The closed form

A path is exactly a choice of which of the `(m - 1) + (n - 1)` moves are
"down". So:

```python
return comb(width + height - 2, height - 1)
```

`O(min(m, n))` arithmetic, no table. It is the better answer **for this
problem** and it is a dead end: add a single obstacle, or a cost per cell, and
the binomial is gone while the recurrence needs one extra line.

That is the honest trade, and worth being explicit about rather than
pretending the DP is optimal: *the closed form is faster and the table
generalises.* Which you want depends on whether the problem is the last one of
its kind you will see.

Note `math.comb` rather than factorials with division — `test_handles_a_large_grid_exactly`
uses a 60×60 grid, whose answer is around 10³⁴. Python integers are exact;
floating-point division is not, and a float-based closed form is simply wrong
there.

## What to take away

**When a DP table's recurrence has a bounded reach, collapse the table to that
reach.** One row for a two-dimensional grid, two scalars for a linear
recurrence. The saving is usually large and the cost is having to be careful
about sweep direction — which is the one thing to check, every time, by asking
what each operand holds at the instant it is read.
