"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class TreeNode:
    """A binary tree node."""

    def __init__(
        self,
        value: int,
        left: TreeNode | None = None,
        right: TreeNode | None = None,
    ) -> None:
        self.value = value
        self.left = left
        self.right = right


def kth_smallest(root: TreeNode | None, k: int) -> int:
    """Return the kth smallest value in the BST, 1-based.

    **An in-order traversal of a BST visits its values in increasing order.**
    That is the whole insight, and it means the problem needs no comparison, no
    sort and no notion of "smallest" anywhere in the code -- the kth node
    visited simply *is* the kth smallest. Nothing here would work on an
    arbitrary binary tree, and nothing here mentions the BST property either;
    it is entirely carried by the traversal order.

    Written with an **explicit stack** rather than recursion, for one reason:
    the early exit. Recursion can do this, but the answer has to be propagated
    back up through every frame -- a sentinel return value, or an exception, or
    a mutable counter in an enclosing scope. With a stack, "stop now" is a
    plain `return` and the remaining nodes are simply never pushed.

    That matters because stopping is part of the specification. Collecting
    every value and indexing is O(n) time and O(n) space; this is O(h + k) time
    and O(h) space -- walk down the left spine, then pop k times. On a large
    tree with k = 1 that is the difference between reading a million nodes and
    reading the depth of the tree.

    The loop structure is the standard iterative in-order: push the entire left
    spine, then pop a node (visit it) and move to its right child, whose own
    left spine is pushed on the next pass. Each node is pushed and popped once.
    """
    stack: list[TreeNode] = []
    node = root
    remaining = k
    while stack or node is not None:
        while node is not None:
            stack.append(node)
            node = node.left
        node = stack.pop()
        remaining -= 1
        if remaining == 0:
            return node.value
        node = node.right
    raise ValueError(f"the tree holds fewer than {k} values")
