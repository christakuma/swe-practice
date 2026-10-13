# Find the coordinate that stays the same

Revealed after grading. This is "Diagonal Traverse" (LeetCode 498).

The spiral was best handled by four boundaries closing in, because a spiral
is made of straight runs along edges. A diagonal walk can be simulated the
same way — step, hit an edge, turn — and the turning rules are a small
nightmare: at the top edge go right, unless you are also at the right edge,
in which case go down; mirrored for the other direction.

There is a description of a diagonal that needs no walking at all:

> every cell on it has the same `row + column`.

```
sums:  0 1 2
       1 2 3
       2 3 4
```

So diagonal `d` is the cells with `row + column == d`, there are
`rows + columns - 1` of them, and the traversal is: list each diagonal, flip
every other one.

```python
for diagonal in range(rows + columns - 1):
    first_row = max(0, diagonal - columns + 1)
    last_row = min(diagonal, rows - 1)
    cells = [matrix[row][diagonal - row] for row in range(first_row, last_row + 1)]
    if diagonal % 2 == 0:
        cells.reverse()
```

The clipping of the row range is the only place the shape of the matrix
appears, and it handles wide, tall and square identically.

## Where it goes wrong

- **Square-only bounds.** `range(diagonal + 1)` for the rows is right until
  the diagonal is longer than the matrix is tall, or its column runs off the
  side.
- **Parity the wrong way round.** Rows ascending is down-and-left. The first
  diagonal after the corner travels that way, so the *even* ones are the ones
  to reverse.

## What the twist was testing

Looking for an invariant before writing a simulation. `row + column` for
anti-diagonals, `row - column` for the main ones, `min(r, c, R-1-r, C-1-c)`
for the rings of a spiral: most "read the grid in a funny order" problems
have a coordinate that is constant along each piece of the path, and finding
it turns a state machine into a loop.
