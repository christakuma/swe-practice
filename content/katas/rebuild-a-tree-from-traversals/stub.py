"""Your solution goes here.

The tests import both `TreeNode` and `rebuild` from this module, so keep the
class as it is -- it is what the tests inspect.
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


def rebuild(preorder: list[int], inorder: list[int]) -> TreeNode | None:
    """Rebuild the tree from its pre-order and in-order traversals.

    Args:
        preorder: the values in pre-order (root, left subtree, right subtree).
        inorder: the same values in in-order (left subtree, root, right
            subtree). All values are distinct.

    Returns:
        The root of the reconstructed tree, or None for empty input.
    """
    raise NotImplementedError
