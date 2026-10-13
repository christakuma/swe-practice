# Give every line a number

Revealed after grading. "Set Matrix Zeroes" (LeetCode 73) with the reach of
a queen — the same bookkeeping N-Queens uses.

## Four families of lines

Rows and columns were easy because they come with names: row 3, column 5.
The step this problem asks for is naming a diagonal.

Walk down and right: row goes up by one, column goes up by one. Their
**difference** does not change.

Walk down and left: row goes up by one, column goes down by one. Their
**sum** does not change.

| line | every cell on it has the same… |
|---|---|
| row | `row` |
| column | `column` |
| diagonal falling right | `row - column` |
| diagonal falling left | `row + column` |

Four numbers per cell, four lists of flags.

```python
if matrix[row][column] == 0:
    row_hit[row] = True
    column_hit[column] = True
    falling_hit[row - column + columns - 1] = True
    rising_hit[row + column] = True
```

Then a second pass clears any cell with a flagged line. Two passes, as
always, so that zeros you write are never read as original.

## The `+ columns - 1`

`row + column` runs from 0 up, and indexes a list as it is.

`row - column` runs from `-(columns - 1)` to `rows - 1`. Shift it.

The reason to dwell on it: without the shift nothing crashes. Python reads
`flags[-1]` as the last element. A list of length `max(rows, columns)`
indexed by raw `row - column` runs cleanly and treats the diagonal one step
above the main one as the same line as some diagonal far below it. Two of
the tests are a single zero placed to make exactly that mistake visible.

(A dictionary or a set keyed by `row - column` avoids the question, at the
cost of hashing. Either is fine; know which you are using and why.)

## Why not constant space

The standard problem's best answer stores its flags in the matrix: the
first row remembers which columns to clear, the first column which rows.
That is `m + n - 1` cells of storage, exactly enough.

There are `m + n - 1` diagonals in each direction. The matrix has nowhere
to put twice as many flags again, so the trick stops here, and `O(m + n)`
on the side is the right answer. Knowing *why* a trick does not extend is
worth as much as knowing the trick.

What is still worth refusing is `O(m * n)`: a copy of the matrix, or a list
of every zero's position. The second looks small and is not — a matrix can
be mostly zeros.

## What the twist was testing

Finding the invariant. "Which cells are on this diagonal?" sounds like it
needs a walk from each zero to the edges. Asking instead "what is the same
about all of them?" turns a geometric question into an index, and the
problem back into the one you had already solved, twice over.
