# The walk is the same; only the verb changes

Revealed after grading. This is "Spiral Matrix II" (LeetCode 59).

Reading in spiral order and writing in spiral order are one traversal: four
boundaries that close in as each side is finished. Where the reader did
`result.append(matrix[row][column])`, the writer does
`matrix[row][column] = value`.

Two things bite.

**`[[0] * n] * n` is one row, n times.** Every write lands in all of them and
the result is the last ring's values repeated down the grid. Build the rows
with a comprehension.

**The guards the reader needed are not needed here.** Reading an arbitrary
matrix has to check, before the bottom and left passes, that the ring has not
collapsed to a single row or column. A square cannot collapse that way: its
rings close on all four sides together, and when an odd square is down to its
one centre cell the top pass fills it and the other three run over empty
ranges. Carrying the guards across is harmless; believing they are doing
something is the mistake.
