# Your position is more than where you are

Revealed after grading. LeetCode's "Shortest Path in a Grid with Obstacles
Elimination" (1293) is this with `k` breaks.

Breadth-first search finds shortest paths because of one rule: mark a node
visited when you first reach it, and never go back. The first arrival is the
shortest, and any later arrival could only do what the first one already
did.

The break makes that last sentence false. Take

```
S . # .
# . . #
. # # E
```

The middle of the grid can be reached by open cells, or just as quickly
through either of the walls next to the start. The destination is walled in,
so only a route that arrives beside it with its break intact can finish. If
the search has already marked those middle cells as "visited" on behalf of a
route that came through a wall, the route that could have finished is
thrown away.

"First arrival wins" is still true — for the right notion of *where you
are*. Two routes are interchangeable only if they are at the same cell
**with the same number of breaks left**. So that pair is the node:

```python
state = (r, c, used + grid[r][c])
if state[2] <= 1 and state not in seen:
```

The graph has twice as many nodes. Nothing else about the search changes.

## The decoys

- **Try removing each wall and re-run.** Correct, and `O(walls * cells)`:
  the tests' oracle does exactly this on 3 x 3 grids.
- **Two searches, from each end, and join them across each wall.** Also
  correct and linear — sum the distance from the start to one side of a wall
  and from the end to the other. A good answer, and a harder one to extend
  to two breaks.
- **Dijkstra with walls costing more.** Answers a different question: the
  cheapest route, not the shortest route with a limited number of walls.

## What the twist was testing

State-space search. A great many "BFS with a twist" problems — keys and
doors, a limited number of jumps, one free flight — are plain BFS on a
graph whose nodes are (place, some small extra fact). The skill is naming
the extra fact, and noticing that `visited` has to be keyed on all of it.
