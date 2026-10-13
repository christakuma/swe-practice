"""Your solution goes here.

The tests import the node class from this module too, so keep it as it is --
it is how the tests build what they hand you.
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


def kth_largest(root: TreeNode | None, k: int) -> int:
    """Return the kth largest value in the BST, 1-based.

    Args:
        root: the root of a valid binary search tree with distinct values.
        k: which value to return, counting from 1 at the largest. Always
            within the tree's size.

    Returns:
        The kth largest value.
    """
    raise NotImplementedError
