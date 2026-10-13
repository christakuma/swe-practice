"""Your solution goes here.

The tests import both `TreeNode` and `swapped_values` from this module, so
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


def swapped_values(root: TreeNode | None) -> tuple[int, int] | None:
    """Return the two values whose exchange broke a search tree.

    Args:
        root: the root of a tree that is a valid search tree with distinct
            values, or was one before two of its values were exchanged.

    Returns:
        The two exchanged values, smaller first, or None if the tree is
        valid as it stands.
    """
    raise NotImplementedError
