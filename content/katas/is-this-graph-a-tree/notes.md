# Is This Graph a Tree — two properties, one pass

Revealed after grading. The problem is the classic one (LeetCode 261); the
wording above is ours. It is the sequel to
[count connected components](../count-connected-components/notes.md) and it is
mostly here for one warning: the famous shortcut for this problem is
**unsafe on its own**, and it is the first thing most people reach for.

## The definition

A tree is **connected** and **acyclic**. Both, and they are independent — a
forest is acyclic and disconnected; a cycle with a tail is connected and
cyclic. Any solution has to establish both.

## Union-find answers both in one pass

```python
for a, b in edges:
    ra, rb = find(a), find(b)
    if ra == rb:
        return False            # acyclic: fails here
    union(ra, rb)
    components -= 1
return components == 1           # connected: checked here
```

**Acyclic** falls straight out of the structure: a cycle is exactly an edge
whose endpoints are *already* in the same component. There is no separate cycle
search — the same `find` that supports unioning answers it.

**Connected** is then a count. One component left means one piece.

That the two properties fall out of one traversal of the edge list is the
reason to use union-find here rather than a DFS with a parent check, which
needs an adjacency list and a visited set and still has to count reachable
nodes afterwards.

## The shortcut, and why it is a trap

> A graph with `n` nodes and exactly `n - 1` edges is a tree **if and only if
> it is connected.**

True, and useful — any connected acyclic graph has exactly `n - 1` edges, so
the edge count can replace the cycle check *once connectivity is established*.

The trap is using the count **alone**:

```python
return len(edges) == n - 1        # wrong
```

Four nodes, three edges — exactly `n - 1` — and neither connected nor acyclic:

```
(0,1), (0,1), (2,3)
```

Two copies of one edge is a cycle, and `2-3` is a separate island.
`test_rejects_a_graph_with_the_right_edge_count_but_wrong_shape` is that case.

**The count rules out "too few edges" and "too many edges". It says nothing
about how they are arranged.** A conservation law constrains the total; it does
not constrain the distribution. That is a general shape of error worth
recognising — the arithmetic invariant is necessary and not sufficient, and it
is seductive precisely because it is so cheap.

## Repeated edges are cycles

`(0, 1)` twice means two distinct paths between the same pair, which is a
cycle. Union-find gets this right for free: the second copy finds the endpoints
already joined.

Worth noting because the instinct is to clean the input first —
`edges = set(edges)` — and that silently turns a non-tree into a tree.
`test_rejects_a_repeated_edge` holds it. **Deduplicating an input is a
modelling decision, not tidying up**; here it discards the exact fact being
tested.

## The empty graph

`n == 0` is vacuously a tree, and it needs the explicit guard: with no nodes
the component count is `0`, not `1`, so `components == 1` reports False.

This is the one place in the kata where the answer is a convention rather than
a derivation. It is worth stating in the prompt — which it is — because
"vacuously true" and "meaningless" are both defensible and the tests have to
pick one.

## What to take away

**When a definition has two clauses, check two things.** The shortcut that
collapses them into one number is a theorem about the conjunction, not a
replacement for either half — and reaching for it before establishing the other
clause is how `len(edges) == n - 1` ends up in production.

The transferable instinct: if a cheap counting check seems to settle a
structural question, ask what rearrangement of the same count would break it.
There usually is one.
