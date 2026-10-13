# What a node reports is not what a node records

Revealed after grading. This is "Diameter of Binary Tree" (LeetCode 543),
counted in nodes rather than edges.

The largest-path-sum problem and this one are the same traversal. In both,
every node does two different things:

```python
best = max(best, left + right + 1)   # the path that turns here
return 1 + max(left, right)          # the path a parent could extend
```

A path can turn at most once. So a node may be the turning point — using both
its children's downward paths — or it may be part of a longer path that turns
higher up, in which case it can contribute only one side. The first is
recorded, the second is returned, and mixing them up is the bug: returning
`left + right + 1` hands a parent a path with a fork in it.

## What the twist was testing

That the structure was understood apart from the arithmetic. Sums can be
negative, which is why the original clamps a child's contribution at zero;
lengths cannot, so that guard disappears. Carrying it across is harmless.
Carrying across the assumption that the best path goes through the root is
not — the second example's longest path never reaches it.

Check which unit is being asked for. The well-known version counts **edges**,
one fewer than the nodes; this one counts nodes, and an empty tree is 0 either
way.
