"""Your solution goes here.

The tests import both `TreeNode` and `best_path_sum` from this module, so keep
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


def best_path_sum(root: TreeNode) -> int:
    """Return the largest sum along any path from the root down to a leaf.

    Args:
        root: the root of a non-empty tree. Values may be negative.

    Returns:
        The largest total of the values on a path that starts at `root` and
        ends at a node with no children.
    """
    raise NotImplementedError
