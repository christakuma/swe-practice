# Building instead of swapping

Revealed after grading. The "but don't modify the input" follow-up to "Invert
Binary Tree" (LeetCode 226).

```python
return TreeNode(root.value, mirrored(root.right), mirrored(root.left))
```

One line, and it is a different kind of function from the in-place version.
That one *assigned* to existing nodes and returned the root it was given. This
one assigns to nothing and returns something new.

**Shallow copies fail quietly.** `TreeNode(root.value, root.right, root.left)`
creates one new node and reuses the original's subtrees, unmirrored below the
top. It looks right for a tree of three nodes and shares every other node with
its input — so a later change to either tree shows up in both.

In place versus fresh copy is a question to ask before starting any problem
that transforms a structure. The answers have different signatures, different
memory costs, and different bugs.
