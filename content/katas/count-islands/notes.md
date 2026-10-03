# A grid is a graph, and this is connected components

Say that out loud and the problem is solved. Each cell is a node; each pair of
orthogonally adjacent land cells is an edge. "How many islands" is "how many
connected components", and the standard algorithm is:

```
for every node:
    if unvisited:
        count += 1
        explore everything reachable from it
```

The outer loop runs over every cell — O(rows × columns) — and the exploration
visits each land cell exactly once across the whole run, because a visited cell
is never explored again. So the total is linear in the number of cells, which is
the best possible: you have to look at each one to know whether it is land.

DFS or BFS makes no difference to the count. Use whichever; the stack version is
one line shorter.

## Sinking the island

```python
grid[row][column] = 0        # instead of visited.add((row, column))
```

The grid is the visited set. O(1) extra space instead of O(n), no hashing of
tuples, and it **destroys the caller's data** — which this kata permits
explicitly, and real code should too, in the signature or the docstring, rather
than by assumption. The alternative when you cannot mutate is a `set` of
coordinates or a parallel grid of booleans.

Note the detail in the reference: cells are marked `0` **as they are pushed**,
not as they are popped. Marking on pop lets the same cell be pushed several
times by different neighbours — still correct, and the stack can grow to several
times the size of the island for no reason.

## Four neighbours, not eight

```python
for dr in (-1, 0, 1):
    for dc in (-1, 0, 1):      # eight neighbours, plus the cell itself
```

That is the tempting way to generate offsets and it is wrong here: diagonals do
not connect. A diagonal-connected grid is a genuinely different problem with
genuinely different answers — `[[1,0],[0,1]]` is two islands under
four-connectivity and one under eight — and the suite tests for it specifically,
because every other test gives the same answer either way.

Writing the four offsets out, or as `((-1, 0), (1, 0), (0, -1), (0, 1))`, makes
the choice visible instead of emergent.

## Why recursion fails here and not in the tree katas

A tree's depth is usually its log; a grid's connected component can be every
cell. The 300×300 all-land grid in the suite is a single component of ninety
thousand cells, and a recursive flood fill is ninety thousand frames deep at its
worst. Python's default limit is 1000.

`sys.setrecursionlimit(200_000)` is not the fix — you then hit the actual C
stack and get a segfault instead of an exception. An explicit stack is bounded
by heap memory, which is the right resource for this.

## The family

The same walk answers a lot of grid questions, and only the bookkeeping changes:

| question | what you track |
|---|---|
| how many islands | a count per fresh walk |
| biggest island | the size of each walk |
| [flood fill](../flood-fill/notes.md) | overwrite as you go |
| [shortest path](../shortest-path-in-a-grid/notes.md) | **BFS**, and a distance per cell |

The last one is the exception that matters: for shortest paths, DFS and BFS are
not interchangeable. BFS reaches every cell by the fewest steps; DFS reaches it
by whichever path it happened to take.
