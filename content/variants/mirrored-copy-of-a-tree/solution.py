"""Reference solution. CI asserts this passes every test in `tests.py`."""

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


def mirrored(root: TreeNode | None) -> TreeNode | None:
    """Return a new tree that is the mirror image of `root`.

    One new node per original node, built from the mirrored copies of the
    original's children on opposite sides. Nothing is assigned to any
    existing node, which is what leaves the original intact, and the
    recursion reaches every level, which is what leaves nothing shared.
    """
    if root is None:
        return None
    return TreeNode(root.value, mirrored(root.right), mirrored(root.left))
