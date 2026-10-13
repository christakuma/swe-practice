# The ordering already knows where everything is

Revealed after grading. This is "Lowest Common Ancestor of a Binary Search
Tree" (LeetCode 235).

In a plain binary tree the only way to find a value is to look for it, so the
standard solution searches both subtrees of every node and combines what comes
back. A search tree makes that unnecessary:

```python
if high < node.value:
    node = node.left          # both are smaller: go left
elif low > node.value:
    node = node.right         # both are larger: go right
else:
    return node.value         # they part here, or one of them is here
```

One walk downwards. No recursion, no backtracking, and nothing off the path
is examined — which is `O(h)` instead of `O(n)`.

## What the twist was testing

The general solution is correct on a search tree. It also ignores the one fact
the problem added, and the cost of ignoring it is every node in the tree.
"The input has more structure now" is an interviewer's way of asking whether
you will notice — the same test as sorted input in Two Sum.
