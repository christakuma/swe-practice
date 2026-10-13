# Same table, different operator

Revealed after grading. This is "Minimum Path Sum" (LeetCode 64).

The counting version filled a table with
`paths = paths_above + paths_left`. The reasoning behind it — every path into
a cell comes through the cell above or the cell to the left — says nothing
about counting in particular. Ask for the cheapest instead and it reads:

```python
best[column] = left = cost + min(best[column], left)
```

One row is enough, as before. Before the assignment `best[column]` is still
last row's value, which is the cell above; `left` is the value just written.

## Zero was the right border and is now the wrong one

In the counting table, a neighbour outside the grid contributes zero paths,
and adding zero is harmless. Carry that habit over and the outside of the
grid becomes a route that costs nothing: `min(above, 0)` is 0 for every cell
in the first column, and each row appears to start for free.

The identity for `+` is 0. The identity for `min` is infinity. Changing the
operator means changing the padding, and the single real zero is the "cost so
far" before the first cell.

## What the twist was testing

Greed again. *Step to the cheaper of the two neighbours* cannot see past one
move, and a grid can put a cheap cell at the mouth of an expensive corner.
The counting problem had no such temptation, so it is easy to arrive here
without ever having had to argue for the table.
