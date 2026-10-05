# Water Flowing to Both Oceans — search from the answer

Revealed after grading. The problem is the classic one (LeetCode 417); the
wording above is ours. It is the best example in the library of a reframing
that is not a cleverness but a **change of direction**, and it is worth
recognising because the same move solves a whole family of problems.

## The forward solution, and why it is wasteful

Ask, for each cell, "can water escape from here?" — flood downhill and see
which borders you touch. Correct, and `O((m·n)²)` in the worst case: there are
`m·n` searches and each can cover the whole grid. On a flat 200×200 grid, every
one of the 40,000 searches visits all 40,000 cells.

Almost all of that is recomputation. Cell A's search and its neighbour B's
search overlap almost entirely.

## The move

**Reverse the question.** Instead of asking which cells reach the ocean, ask
which cells *the ocean can reach* — walking uphill from the borders.

Uphill is the exact reverse of the flow rule. Water runs to a neighbour at the
same height **or lower**, so the reverse walk goes to a neighbour at the same
height **or higher**:

```python
if heights[next_row][next_column] < heights[row][column]:
    continue                 # cannot have flowed from there to here
```

Two searches — one per ocean, each seeded with its whole border — and the
answer is the intersection of what they reach. Each search visits every cell at
most once, so `O(m·n)`.

**Why this works at all: the two searches are the same relation read in
opposite directions.** "A drains to the ocean" and "the ocean reaches A
uphill" are the same statement about the same edge set. Reversing a reachability
question is always available when the edge relation is invertible, and it turns
`m·n` single-source searches into **two multi-source searches**.

That is the generalisable part. The same reframing solves "which rooms are
reachable from any exit", "which nodes can reach a sink" (search the transpose
graph), and the whole class of problems where the *destinations* are few and
the *sources* are many. Seeding a search with many starting points costs
nothing extra — the visited set is shared — so one search from 800 border cells
is dramatically cheaper than 40,000 searches from one cell each.

## Multi-source is free

Worth saying explicitly because it looks like it should cost something:

```python
seen = set(sources)
stack = list(sources)
```

A BFS or DFS seeded with every border cell at once is one traversal, not `k`
traversals. Nothing about the algorithm changes. This is the same trick as the
rotting-oranges / nearest-exit family, where every source starts at distance
zero and one BFS computes all the distances.

## `>=` and the plateau

Equal heights flow **both ways**, so a flat region is fully connected and a
flat grid drains everywhere. Using a strict `>` in the uphill walk strands
every plateau that does not rise, and on a flat grid returns only the border.

`test_handles_a_flat_grid` is that case, and it is also the worst case for the
forward solution — which makes it the one test doing two jobs.

## Do not mark the grid

Writing a sentinel into `heights` to track visited cells saves a set and
destroys the caller's data. Same judgement as in
[find a word in a grid](../find-a-word-in-a-grid/notes.md), where mutation was
*allowed* because the mark was undone — here it would be permanent, so it
simply corrupts the input. `test_does_not_mutate_the_grid` holds it.

## Iterative, not recursive

A 200×200 grid is 40,000 cells, and an uphill path can snake through all of
them. That exhausts CPython's recursion limit long before the time limit. Grid
searches at any realistic size want an explicit stack — the same conclusion as
[kth smallest in a BST](../kth-smallest-in-a-bst/notes.md) reached for a
different reason.

## What to take away

**When you are running the same search from many sources to few destinations,
reverse it.** Count the sources and the destinations first; if that ratio is
lopsided, the cheap direction is from the small side. The rule of thumb:
*search from whatever there is less of.*
