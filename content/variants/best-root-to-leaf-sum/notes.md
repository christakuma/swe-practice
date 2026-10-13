# The base case is the leaf

Revealed after grading. LeetCode has the decision version of this as "Path
Sum" (112); the maximum is the same recursion.

The standard problem lets a path start anywhere, turn once, and stop wherever
it likes — which is why its solution is full of `max(..., 0)`: every one of
those zeros means "or take nothing". None of that freedom is left here. The
path starts at the root, never turns, and ends where the tree ends.

```python
below = [best(child) for child in (node.left, node.right) if child is not None]
return node.value + (max(below) if below else 0)
```

## The bug this problem exists to find

```python
def best(node):
    if node is None:
        return 0
    return node.value + max(best(node.left), best(node.right))
```

It is the first thing anyone writes and it is right on every tree whose nodes
have zero or two children. Give a node one child with a negative total and the
missing side "wins" with its zero — the path stops at a node that is not a
leaf. `TreeNode(10, TreeNode(-5))` is 5, and this returns 10.

Returning negative infinity for `None` fixes the one-child case and breaks the
leaf, which now has two infinitely bad children. The clean statement is the
one in the definition: **a leaf is the base case, and a missing child is not a
candidate.**

## What the twist was testing

Whether the zeros in the standard solution were understood or copied. There
they mean "a path may choose not to extend". Carry them over and they quietly
grant the same permission here, where the problem has just taken it away.
