# Two sorted streams and a merge

Revealed after grading.

One search tree hands you its values in ascending order: walk it in-order.
The standard problem is "take the kth thing off that walk and stop". Two
trees are two such walks, and the kth smallest overall is the kth thing off
their **merge** — the same merge as in merge sort, taking whichever front
value is smaller.

```python
merged = heapq.merge(_ascending(first), _ascending(second))
return next(islice(merged, k - 1, None))
```

## The real work is making the walk pausable

A recursive in-order traversal cannot be interleaved with another one: it
runs to completion. The merge needs to take one value from tree A, then maybe
three from tree B, then one from A again. So the traversal has to be
something that can be *resumed* — a generator around an explicit stack:

```python
while stack or node is not None:
    while node is not None:
        stack.append(node)
        node = node.left
    node = stack.pop()
    yield node.value
    node = node.right
```

Each `yield` hands back one value and freezes the walk exactly where it is.
It descends only as far as the next value requires, which is why a huge
subtree the answer never reaches costs nothing.

This is "BST Iterator" (LeetCode 173) used twice, and it is the form of
in-order traversal worth having in your fingers, because it is the only one
that composes.

## Duplicates

A value in both trees is two values. `set(a) | set(b)` and a merge that skips
equal fronts both lose one of them.

## What the twist was testing

Whether the traversal was owned as a tool or only as a recursive template.
"Now there are two" is a common follow-up precisely because it cannot be
answered by running the old solution twice and combining the results — the
kth of the union is not a function of the kths of the parts.
