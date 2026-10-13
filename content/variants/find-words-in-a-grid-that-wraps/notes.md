# The edge was never part of the algorithm

Revealed after grading. "Word Search II" (LeetCode 212) on a torus.

The flat version has this in the middle of it:

```python
next_row, next_column = row + row_step, column + column_step
if 0 <= next_row < rows and 0 <= next_column < columns:
    search(next_row, next_column, child)
```

and the wrapped version has this:

```python
search((row + row_step) % rows, (column + column_step) % columns, child)
```

That is the whole change. Python's `%` gives a non-negative result for a
negative left side, so `-1 % rows` is the last row and no special case is
needed for going up or left. (In C or Java it would be `-1`, and you would
write `(row + step + rows) % rows`.)

## Why nothing else needed to change

The search marks a cell by overwriting it, and restores it on the way out.
The mark is *on the cell*, so however a path arrives — straight, or round the
back — it finds the same mark.

That is what handles the cases that look like special cases:

- **One column.** Left and right of a cell is the same cell. It is marked,
  the search refuses it, and nothing was written to make that happen.
- **Two columns.** Left and right are the same neighbour. It gets searched
  twice. A word found is cleared from the trie the first time, so the second
  search finds nothing new.
- **All the way round.** `a b c` in a ring: "abca" goes right three times and
  arrives at the a it started from, which is still marked.

## The version that breaks

```python
visited.add((row, column))          # before wrapping
...
if (next_row, next_column) not in visited:
```

If the coordinates in the set are the unwrapped ones — `(0, 3)` for the cell
that is really `(0, 0)` — then the same cell has several names and the set
does not recognise it. Every flat-grid test passes. The ring of three is what
fails — and the test puts that ring in a grid of six cells, because on a grid
of three "abca" is also longer than the grid, and a length check would have
refused it for the wrong reason.

## What the twist was testing

Whether you know which lines of your solution are the algorithm and which are
the shape of the board. Here it was one line and one `if`. An interviewer
changing the topology is asking whether you can find that line quickly, and
whether your "visited" was about cells or about coordinates that happened to
be cells.
