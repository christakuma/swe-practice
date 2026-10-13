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


def kth_smallest(first: TreeNode | None, second: TreeNode | None, k: int) -> int:
    """Return the kth smallest value across two BSTs, 1-based.

    Args:
        first: the root of a valid binary search tree, or None.
        second: the root of another, or None. A value may be in both trees.
        k: which value to return, counting from 1 at the smallest. Always
            within the combined size.

    Returns:
        The kth smallest of all the values, with a value held by both trees
        counted twice.
    """
    raise NotImplementedError
