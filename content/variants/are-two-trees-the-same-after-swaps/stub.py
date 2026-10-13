"""Your solution goes here.

The tests import both `TreeNode` and `is_same_tree` from this module, so keep
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


def is_same_tree(first: TreeNode | None, second: TreeNode | None) -> bool:
    """Return whether swapping children at some nodes makes the trees equal.

    Args:
        first: the root of one tree, or None for an empty tree.
        second: the root of the other, or None.

    Returns:
        True if `second` becomes identical to `first` after exchanging the
        left and right subtrees of any number of its nodes.
    """
    raise NotImplementedError
