# The edge that joins nothing

Revealed after grading. This is "Redundant Connection" (LeetCode 684).

Deciding whether a graph is a tree needed union-find to spot *any* edge whose
ends were already connected. This asks which edge that is — and the same loop
already knows:

```python
if first == second:
    return (a, b)
```

Why this is the right one: it is the edge that closes the cycle, so it is on
the cycle and can go; and every other cycle edge came before it, so it is the
last such edge in the input.

**"Seen" is not "connected".** A tempting shortcut keeps a set of nodes that
have appeared and returns the first edge with both ends in it. Edges
`(0, 1), (2, 3), (1, 2), (0, 3)` defeat it: when `(1, 2)` arrives, both ends
have been seen, but in different pieces. Connectivity is a question about
components, and that is exactly what the structure is for.
