# Read the queue's length before you drain it

Breadth-first search already visits nodes in level order. What it does not give
you is where one level ends — and the fix is one line:

```python
while queue:
    width = len(queue)          # the queue holds exactly this level, right now
    for _ in range(width):
        node = queue.popleft()
        ...append children to the back...
```

At the top of each round, every node in the queue is on the same level, because
the previous round added exactly their children and nothing else. Reading the
length *before* appending anything freezes that boundary.

Getting this from the structure rather than from a counter matters because the
counter version is where the bugs are: levels are not 1, 2, 4, 8 unless the tree
is complete, and a lopsided tree breaks any guess based on powers of two.

## The other correct approach

Push `(node, depth)` pairs and bucket by depth:

```python
levels: dict[int, list[int]] = defaultdict(list)
queue = deque([(root, 0)])
while queue:
    node, depth = queue.popleft()
    levels[depth].append(node.value)
    ...
return [levels[d] for d in sorted(levels)]
```

Works, carries a depth per node, and turns a traversal into a grouping problem.
Its real advantage is that it works with **depth-first** traversal too — the
depth is explicit, so you no longer need to visit in level order at all:

```python
def walk(node, depth):
    if node is None:
        return
    if depth == len(levels):
        levels.append([])
    levels[depth].append(node.value)
    walk(node.left, depth + 1)
    walk(node.right, depth + 1)
```

Which is worth seeing, because it is the shortest level-order solution and it
does not use a queue at all. The left-to-right ordering within a level comes
from visiting `left` before `right`, and the levels appear in order because
depth is the index.

## `deque` is not a style preference

`list.pop(0)` is O(n): Python lists are contiguous, so removing the front
element moves everything else. Used as a queue, it makes a linear traversal
quadratic — on the sixteen-thousand-node tree in the suite, about eight thousand
elements shift on every one of eight thousand pops.

`collections.deque` is a doubly-linked list of blocks, so `popleft` is O(1).
This is the most common accidental quadratic in Python, and the fix is an
import.

## What level order is good for

Anything where distance from the root is the thing you care about:

- the shallowest node satisfying some property — BFS finds it first, DFS may
  find a deeper one and have to keep looking
- shortest path in an unweighted graph, which is the same statement about a
  graph instead of a tree
- rendering a tree, printing it, serialising it by level
- "right-hand view" of a tree — the last element of each level

The complement is worth knowing too: DFS is the one to use when you need to
aggregate *up* from the leaves, like
[depth](../max-depth-of-a-binary-tree/notes.md) or a subtree sum, because the
recursion already returns in the right direction.

## Complexity

O(n) time, every node enqueued and dequeued once. O(w) space where w is the
widest level — which for a complete tree is n/2, so O(n) in the worst case. DFS
would be O(h) space instead, and that trade — width for height — is the real
difference between the two traversals.
