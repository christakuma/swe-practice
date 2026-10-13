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


def is_mirror(first: TreeNode | None, second: TreeNode | None) -> bool:
    """Return whether `second` is `first` reflected left to right.

    Args:
        first: the root of the first tree, or None.
        second: the root of the second tree, or None.

    Returns:
        True if the two hold the same values with left and right exchanged
        at every node.
    """
    raise NotImplementedError
