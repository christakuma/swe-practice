"""Your solution goes here.

The tests import both `TreeNode` and `right_side_view` from this module, so
keep the class as it is -- it is how the tests build trees to hand you.
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


def right_side_view(root: TreeNode | None) -> list[int]:
    """Return the rightmost value on each level, top to bottom.

    Args:
        root: the root of the tree, or None for an empty tree.

    Returns:
        One value per level: the last node on that level when it is read
        left to right.
    """
    raise NotImplementedError
