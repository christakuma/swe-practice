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


UNBALANCED = -1


def is_balanced(root: TreeNode | None) -> bool:
    """Return whether the tree is height-balanced.

    The depth recursion, made to carry a second piece of news. `depth`
    returns a subtree's depth as usual, or `UNBALANCED` if some node inside
    it failed the test. A real depth is never negative, so the two cannot be
    confused.

    Each node asks its children once. If either reports `UNBALANCED`, or
    their depths are more than one apart, it reports `UNBALANCED` itself;
    otherwise it reports its own depth. One visit per node, and a failure
    anywhere reaches the root without any node being measured twice.
    """

    def depth(node: TreeNode | None) -> int:
        if node is None:
            return 0
        left = depth(node.left)
        right = depth(node.right)
        if UNBALANCED in (left, right) or abs(left - right) > 1:
            return UNBALANCED
        return 1 + max(left, right)

    return depth(root) != UNBALANCED
