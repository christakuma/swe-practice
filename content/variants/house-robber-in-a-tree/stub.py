"""Your solution goes here.

The tests import both `TreeNode` and `best_haul` from this module, so keep the
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


def best_haul(root: TreeNode | None) -> int:
    """Return the largest total of nodes no two of which share an edge.

    Args:
        root: the root of a tree of non-negative values, or None.

    Returns:
        The largest sum of a set of nodes in which no node is chosen together
        with its parent.
    """
    raise NotImplementedError
