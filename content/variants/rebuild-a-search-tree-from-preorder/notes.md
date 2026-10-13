# The ordering is the second traversal

Revealed after grading. This is "Construct Binary Search Tree from Preorder
Traversal" (LeetCode 1008).

For an arbitrary tree, pre-order tells you the root and nothing about where
its left subtree ends; the in-order list supplied that. A search tree
supplies it by itself: after the root come all the smaller values (the left
subtree), then all the larger ones.

You could sort the list to get the in-order traversal and call the standard
solution. It works, at `O(n log n)`, and it is a way of not noticing what
changed.

## Linear, with a stack

```python
if value < path[-1].value:
    path[-1].left = node
else:
    parent = path.pop()
    while path and path[-1].value < value:
        parent = path.pop()
    parent.right = node
path.append(node)
```

The stack is the current path from the root, minus any node whose right side
has already been started. Its values decrease towards the top.

- **A smaller value** goes left of the top. Pre-order always tries left
  first.
- **A larger value** cannot be under any node it exceeds on that node's
  left. So those nodes are finished: pop them. It belongs to the right of
  the *last* one popped — the deepest ancestor it is larger than.

After `5, 3, 1`, the value `4` pops the 1 and the 3, stops at the 5, and
hangs to the right of the 3.

## Linear, with bounds

The recursive version passes each call an upper bound: build a node from the
next value, recurse left with the node's own value as the bound, recurse
right with the bound you were given, and stop as soon as the next value
exceeds your bound. Same single pass; the bounds are the stack, held in call
frames — which is why it fails on a chain a hundred thousand deep and the
explicit stack does not.

## What the twist was testing

Whether "you need two traversals" was understood as a fact about information.
One traversal of an arbitrary tree is ambiguous. One traversal of a search
tree is not, because the search property is itself `n log n` bits of
structure you were given for free.
