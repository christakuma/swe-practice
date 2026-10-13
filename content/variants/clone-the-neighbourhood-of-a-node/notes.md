# Distance is a breadth-first idea

Revealed after grading.

Cloning the whole graph does not care what order the nodes are met in. Depth
first, breadth first, any order at all: every node gets copied once, and the
map from originals to copies stops the cycles. That freedom is why the
standard solution is five lines of recursion.

A radius takes the freedom away, and the natural edit to those five lines is
wrong:

```python
def copy(original, budget):
    if id(original) in copies:
        return copies[id(original)]
    duplicate = copies[id(original)] = Node(original.value)
    if budget > 0:
        duplicate.neighbours = [copy(n, budget - 1) for n in original.neighbours]
    return duplicate
```

Take a triangle `0, 1, 2` with a `3` hanging off the `2`, and copy from `0`
with radius 2. The recursion goes `0 -> 1 -> 2` and reaches `2` with nothing
left to spend. It registers the copy and returns. When `0` later looks at its
*direct* edge to `2` — the route that makes `2` one step away — the map says
"already copied", and `3` is never visited.

A node's first visit in a depth-first walk is by *some* route. Its first visit
in a breadth-first walk is by a *shortest* one. Any question with "within k
steps" in it is a breadth-first question.

## Two passes

1. Breadth-first for `radius` rounds, creating a copy of each node as it is
   first met.
2. For each copied node, build its neighbour list from the original's,
   keeping the neighbours that have a copy.

Wiring in a second pass is what gets the rim right. Two nodes that are both
exactly `radius` away may be joined to each other, and neither is expanded by
the search — but both have copies, so pass two keeps the edge.

## What the twist was testing

Whether you knew *why* the standard solution was allowed to be depth-first.
