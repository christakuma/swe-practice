# BFS is not a style choice here

Depth-first and breadth-first search visit the same cells and answer different
questions. For "is there a route" they are interchangeable. For "what is the
shortest route" they are not:

```
0 0 0 0
0 1 1 0      over the top: 9 cells
0 0 0 0      down the left: 6 cells
```

DFS commits to a direction and follows it to the end. Whichever route it tries
first is the one it reports, and making it correct means continuing after the
first success and revisiting cells whenever a shorter route appears — which is a
different, much slower algorithm.

BFS explores by distance. It finishes every cell at distance d before starting
any at distance d + 1, so **the first time it reaches a cell is by the fewest
steps**. That is the property, and it is why the answer can be returned the
moment the destination comes off the queue.

## Mark on push, not on pop

```python
queue.append((r, c, steps + 1))
grid[r][c] = 1               # <- here, not after popping
```

If a cell is marked only when it is dequeued, then every neighbour that reaches
it pushes a copy first. On a grid, up to four copies per cell; on a graph, one
per incoming edge. The result is still correct — the first copy out of the queue
has the smallest distance — and the queue holds O(E) entries instead of O(V).

On the 200×200 open grid in the suite that is the difference between forty
thousand and a hundred and sixty thousand queue entries. On a denser graph it is
the difference between finishing and not.

## Where the distance lives

Carrying `steps` in the queue works because nothing needs to look a distance up
again. Two variants change that:

- **you want the route, not its length** → store a predecessor per cell and walk
  back from the destination
- **you want the distance to *every* cell** → a distance grid, which is also the
  natural visited marker: `-1` for unvisited

Both are the same search with different bookkeeping.

## When BFS stops being enough

BFS gives shortest paths only when **every edge costs the same**. The moment
steps have different costs — diagonal moves costing more, terrain that is slow
to cross, roads with distances — the "finish distance d before starting d + 1"
argument collapses, and the algorithm is **Dijkstra**: the same search with a
priority queue instead of a plain one, taking the cheapest-so-far cell rather
than the earliest-found.

That relationship is worth holding on to: Dijkstra is BFS with a heap, and BFS
is Dijkstra when all the weights are 1. And if some weights are negative,
neither works, because the cheapest route to a cell can get cheaper after you
have finalised it — which is what Bellman-Ford exists for.

| edge costs | algorithm |
|---|---|
| all equal | BFS |
| non-negative, varying | Dijkstra (BFS + heap) |
| any, including negative | Bellman-Ford |
| equal, and you know roughly where the target is | A* |

## Complexity

O(rows × columns) time and space: every cell is enqueued at most once and each
has at most four neighbours, so both are linear in the number of cells. The
space is genuinely used — a snake-shaped corridor through the grid puts most of
the cells in the queue at once.
