"""Your solution goes here.

The tests import both `TreeNode` and `lowest_common_ancestor` from this module,
so keep the class as it is -- it is how the tests build trees to hand you.
"""

from __future__ import annotations


class TreeNode:
    """A binary tree node. Values are distinct within a tree."""

    def __init__(
        self,
        value: int,
        left: TreeNode | None = None,
        right: TreeNode | None = None,
    ) -> None:
        self.value = value
        self.left = left
        self.right = right


def lowest_common_ancestor(
    root: TreeNode | None, first: int, second: int
) -> int | None:
    """Return the value of the deepest node that has both values below it.

    A node counts as its own ancestor: if `first` is an ancestor of `second`,
    the answer is `first`.

    Args:
        root: the root of the tree, or None.
        first: a value in the tree.
        second: a value in the tree.

    Returns:
        The ancestor's value, or None if either value is not in the tree.
    """
    raise NotImplementedError
