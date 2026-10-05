# Count Connected Components — the structure that flattens itself

Revealed after grading. The problem is the classic one (LeetCode 323); the
wording above is ours. It is the library's introduction to **union-find**, and
the reason to meet it here rather than as a data-structures exercise is that
the counting argument makes the whole thing fall out in one line.

## The counting argument

With no edges at all, there are `n` components — one per node. Then:

> **Every edge that joins two different components reduces the count by one.
> Every edge joining nodes already together changes nothing.**

That is the entire algorithm. No traversal, no adjacency list, no visited set.
All you need is to answer "are these two together?" and "put them together",
repeatedly.

```python
parent = list(range(n))
components = n
for a, b in edges:
    ra, rb = find(a), find(b)
    if ra == rb:
        continue                 # redundant edge
    parent[rb] = ra
    components -= 1
```

The redundant-edge check is not an optimisation — it is the difference between
counting components and counting `n - len(edges)`. A triangle has three edges
and one component; `test_ignores_a_redundant_edge` reports `-1` without it.

## Path compression, which is the interesting part

```python
def find(node):
    while parent[node] != node:
        parent[node] = parent[parent[node]]    # <- this line
        node = parent[node]
    return node
```

Each traversal points the nodes it passes at their *grandparents*, halving the
chain. So **the structure gets cheaper the more it is queried** — using it is
what flattens it.

That is genuinely unusual and worth sitting with. Most data structures are
built by their writes and merely read afterwards; here the reads do the
reorganising, and the cost model is amortised rather than per-operation. It is
also why the complexity is stated as "almost constant": the true bound is
inverse Ackermann, which is below 5 for any input that fits in a computer.

## Union by size, which stops the problem arising

```python
if size[ra] < size[rb]:
    ra, rb = rb, ra
parent[rb] = ra
size[ra] += size[rb]
```

Always attaching the smaller tree under the larger keeps depth logarithmic
before compression even runs. Without it, unioning `0-1`, `1-2`, `2-3`, … can
build a linear chain and `find` degrades to `O(V)`.

The two refinements fix the same problem from opposite ends — one prevents tall
trees, the other repairs them — and either alone is good enough for most
inputs. Both is what makes the bound provable.

## When to use this instead of a traversal

A BFS or DFS over an adjacency list also counts components, in `O(V + E)`
outright with no amortisation. It is simpler and it is the right answer for
this problem as stated.

**Union-find wins when the edges arrive over time.** It answers connectivity
after *each* edge without rebuilding anything, which a traversal cannot do —
it would have to re-run from scratch. That is why union-find is what Kruskal's
minimum-spanning-tree algorithm is built on: edges are considered in weight
order and the question "would this edge close a cycle?" is asked once per edge.

So the honest summary: for a static graph, reach for the traversal. Learn
union-find for the dynamic case, and for the problems — cycle detection in an
undirected graph, [is this graph a tree](../is-this-graph-a-tree/notes.md),
redundant-connection, accounts-merge — where "are these two already together?"
is the question being asked.

## The ordering bug

`test_handles_edges_given_out_of_order` gives `(0,1)`, `(2,3)`, `(1,2)`. The
first two create two separate pairs; the third must **merge two existing
components**, not attach a loose node.

A solution that only ever assigns a node to a component it finds — rather than
re-rooting one tree under another — reports 2. It is correct whenever the edges
happen to arrive in a connected order, which is exactly how hand-written test
cases tend to be written.

## What to take away

**Reframe "count the groups" as "count the merges".** Starting from the
maximum and subtracting is often easier than building up, and here it removes
the traversal entirely.

And: **a self-adjusting data structure can have an amortised bound much better
than its worst single operation.** Path compression is the cheapest possible
example — one line, and it changes the complexity class.
