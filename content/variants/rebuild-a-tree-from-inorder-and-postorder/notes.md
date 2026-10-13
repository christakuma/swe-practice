# Read it from the back, and build the right side first

Revealed after grading. This is "Construct Binary Tree from Inorder and
Postorder Traversal" (LeetCode 106).

The pre-order version reads roots off the front of its list. Post-order has
the root at the *end*, so the natural move is to read it backwards — and
reading post-order backwards gives root, right subtree, left subtree.

```python
value = postorder[at]
at -= 1
middle = position[value]
right = build(middle + 1, high)     # right first
left = build(low, middle - 1)
```

**Right before left.** It is the one line that differs in a way that matters,
and getting it the other way round builds a plausible tree from the wrong
values. The order of the two recursive calls must match the order the shared
index consumes the list in.

The dict of in-order positions is unchanged from the pre-order version, and
does the same job: it removes the repeated scan that makes the obvious
recursion quadratic.

Notice also that the arguments are a different pair in a different order.
Passing them to the old function produces a tree, not an error.
