# Cross the pairs, and keep crossing

Revealed after grading. This is the two-tree form of "Symmetric Tree"
(LeetCode 101): a tree is symmetric exactly when its left subtree is the
mirror image of its right.

```python
return (
    first.value == second.value
    and is_mirror(first.left, second.right)
    and is_mirror(first.right, second.left)
)
```

Three lines, and two of them differ from the same-tree check by one word each.

**The recursion must call itself.** The natural mistake is to cross over at
the root and then hand the subtrees to the equality check you already have:
`is_same(first.left, second.right)`. That accepts a tree whose top two
children have swapped while everything beneath them stayed put — flipped once,
not reflected. A mirror image swaps at every node, and the recursion only
does that if each level makes the crossed call again.

**Identical is not mirrored.** Two copies of the same tree are mirror images
only if the tree is symmetric. It is worth saying out loud, because "they
look the same" is exactly what the standard problem trained you to accept.
