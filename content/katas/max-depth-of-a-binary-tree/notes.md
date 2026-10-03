# Structural recursion: say what the answer is, not how to compute it

```python
if root is None:
    return 0
return 1 + max(max_depth(root.left), max_depth(root.right))
```

Those two lines are two sentences about trees:

- the empty tree has depth 0
- any other tree is one deeper than its deeper subtree

Nothing about traversal order, no visited set, no explicit stack. The recursion
follows the shape of the data, which is what makes tree problems the easiest
place to see why recursion is worth having.

## Base case at the empty tree, not at the leaf

It is tempting to write "if this node has no children, return 1". That is also
true, and it costs you:

```python
if root.left is None and root.right is None:
    return 1
```

...a separate branch, a wrong answer for the empty tree (`root.left` raises on
`None`), and four cases instead of two when you get to a node with exactly one
child. Basing it on `None` makes a leaf an ordinary node whose subtrees happen
to be empty.

That generalises: **put the base case at the degenerate structure, not at the
smallest interesting one.** Empty tree, empty list, zero, the empty string. The
code gets shorter and the edge cases stop being edge cases.

## The iterative version, and why you might want it

Recursion costs a stack frame per level. Python's default limit is 1000, so a
degenerate tree — every node with only a left child, which is a linked list
wearing a tree's clothes — raises `RecursionError` at about a thousand nodes
deep. That is not hypothetical: trees built from sorted input are exactly this
shape.

```python
def max_depth(root):
    deepest = 0
    stack = [(root, 1)] if root else []
    while stack:
        node, depth = stack.pop()
        deepest = max(deepest, depth)
        if node.left:
            stack.append((node.left, depth + 1))
        if node.right:
            stack.append((node.right, depth + 1))
    return deepest
```

Same O(n) time, same O(h) space — the stack holds what the call stack held — and
it is bounded by memory rather than by `sys.setrecursionlimit`. The level-by-level
BFS version is a third option and is the one to reach for when you want the
depth *and* something per level.

## Complexity

O(n) time: every node is visited exactly once, and there is no way to do better,
since the deepest leaf could be anywhere.

O(h) space, where h is the height — the recursion stack holds one frame per
level of the current path. O(log n) for a balanced tree, O(n) for a degenerate
one. Quoting O(n) for the space is not wrong, it is just the pessimistic
reading; saying O(h) and then saying what h can be is the more useful answer.
