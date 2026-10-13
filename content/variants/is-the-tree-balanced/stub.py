"""Your solution goes here.

The tests import both `TreeNode` and `is_balanced` from this module, so keep
the class as it is -- it is how the tests build trees to hand you.
"""

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


def is_balanced(root: TreeNode | None) -> bool:
    """Return whether the tree is height-balanced.

    Args:
        root: the root of the tree, or None for an empty tree.

    Returns:
        True if, at every node, the depths of the left and right subtrees
        differ by at most one.
    """
    raise NotImplementedError
