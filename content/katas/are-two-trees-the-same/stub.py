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
    """Return whether two trees have the same shape and values.

    Args:
        first: the root of the first tree, or None.
        second: the root of the second tree, or None.

    Returns:
        True if both trees have identical structure and identical values at
        every position.
    """
    raise NotImplementedError
