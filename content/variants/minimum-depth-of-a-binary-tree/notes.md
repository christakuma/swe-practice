# Shortest is a breadth-first question

Revealed after grading. This is "Minimum Depth of Binary Tree" (LeetCode 111).

It looks like the easiest follow-up there is: the maximum depth is
`1 + max(left, right)`, so the minimum must be `1 + min(left, right)`. That
answer is wrong, and the way it is wrong is the lesson.

## The missing child is not a leaf

```python
def min_depth(node):
    if node is None:
        return 0
    return 1 + min(min_depth(node.left), min_depth(node.right))
```

For a root with one child this returns 1: the empty side reports depth 0, and
`min` happily picks it. But there is no path there. A leaf is a node with *no*
children, and a root with one child is not one.

`max` never had this problem, because an empty side's 0 never wins a `max`.
The symmetric-looking change was not symmetric — the base case had been doing
a job nobody noticed.

## The better tool

Fixing the recursion works and still visits every node. A breadth-first
search does not have to:

```python
queue = deque([(root, 1)])
while True:
    node, depth = queue.popleft()
    if node.left is None and node.right is None:
        return depth
    ...
```

Nodes come off the queue in order of depth, so the first leaf out is the
shallowest. A tree with a leaf at depth two and a hundred thousand nodes
below its other child is answered in three steps — and with no recursion at
all, which a tree that lopsided needs anyway.

## What the twist was testing

That "flip the comparison" is checked rather than assumed, and that *shortest*
and *longest* are different kinds of question. Longest needs the whole tree,
and depth-first is natural. Shortest can stop early, and breadth-first is the
traversal that knows when.
