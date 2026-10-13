# Direction turns one condition into three

Revealed after grading.

An undirected graph is a tree when it is connected and has no cycles, and
there is a tidy shortcut: connected with exactly `n - 1` edges. Give the
edges a direction and "connected" stops being enough. `0 -> 1 <- 2` is
connected, acyclic, has `n - 1` edges, and is not a rooted tree: one node has
two parents and two nodes have none.

A rooted tree needs:

1. exactly one node with no parent;
2. every other node with exactly one;
3. every node reachable from that root.

## Why the third is not implied by the first two

```
0        1 -> 2
         ^    |
         +----+
```

Node 0 has no parent. Nodes 1 and 2 have one each. Conditions 1 and 2 hold,
and this is a root standing next to a loop.

A cycle is the one structure in which every node can have exactly one parent
without any of them being a root. So the parent counts cannot rule it out —
but reachability can, because getting from the root *into* such a cycle would
give some node on it a second parent.

```python
reached = 0
pending = [root]
while pending:
    node = pending.pop()
    reached += 1
    pending.extend(children[node])
return root if reached == n else None
```

No visited set: once condition 2 holds, no node can be reached twice.

## The checks in the other order

Reachability alone is not enough either. Everything reachable from one node,
plus an extra edge back up to the root or across to a cousin, reaches all `n`
nodes and is not a tree. That is what the parent counts catch. Each check
covers exactly what the other misses.

## What the twist was testing

That "tree" is two different definitions depending on whether edges have a
direction, and that a shortcut valid for one (`n - 1` edges and connected)
quietly fails for the other. It is the same care `topological-order` needs:
the moment edges are arrows, connectivity is no longer symmetric.
