# One base case decides which problem this is

Revealed after grading. This is "Substructure of a Binary Tree", the looser
relative of "Subtree of Another Tree" (LeetCode 572).

Both problems are two recursions: an outer one that tries every node of the
tree, and an inner one that compares from there down. The outer one is
identical. The inner one differs in its base cases and nowhere else:

```
                       candidate ran out      tree ran out first
exact subtree          only if tree did too   False
substructure           True                   False
```

```python
if pattern is None:
    return True
if node is None or node.value != pattern.value:
    return False
```

For the exact version, the first line would be `return node is None`. That
single change is the difference between "is this whole subtree" and "does
this shape appear".

When two tree problems sound alike, compare their base cases. That is nearly
always where they part company, and it is the line least likely to be
re-read when adapting one solution into the other.
