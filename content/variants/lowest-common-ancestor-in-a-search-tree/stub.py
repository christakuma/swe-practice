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


def lowest_common_ancestor(root: TreeNode | None, first: int, second: int) -> int:
    """Return the value of the deepest node with both values at or below it.

    Args:
        root: the root of a valid binary search tree with distinct values.
        first: a value in the tree.
        second: a value in the tree. May equal `first`.

    Returns:
        The lowest common ancestor's value. A node is its own ancestor.
    """
    raise NotImplementedError
