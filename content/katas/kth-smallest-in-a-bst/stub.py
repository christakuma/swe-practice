"""Your solution goes here.

The tests import both `TreeNode` and `kth_smallest` from this module, so keep
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


def kth_smallest(root: TreeNode | None, k: int) -> int:
    """Return the kth smallest value in the BST, 1-based.

    Args:
        root: the root of a valid binary search tree with distinct values.
        k: which value to return, counting from 1. Always within the tree's
            size.

    Returns:
        The kth smallest value.
    """
    raise NotImplementedError
