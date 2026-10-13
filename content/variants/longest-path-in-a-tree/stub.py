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


def longest_path(root: TreeNode | None) -> int:
    """Return the number of nodes on the longest path in the tree.

    Args:
        root: the root of the tree, or None for an empty tree.

    Returns:
        The node count of the longest path between any two nodes: 0 for an
        empty tree, 1 for a single node.
    """
    raise NotImplementedError
