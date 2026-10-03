"""Your solution goes here.

The tests import both `TreeNode` and `max_depth` from this module, so keep the
class as it is -- it is how the tests build trees to hand you.
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


def max_depth(root: TreeNode | None) -> int:
    """Return the number of nodes on the longest path from the root down.

    Args:
        root: the root of the tree, or None for an empty tree.

    Returns:
        The depth in nodes: 0 for an empty tree, 1 for a single node.
    """
    raise NotImplementedError
