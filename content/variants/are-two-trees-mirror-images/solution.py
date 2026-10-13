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


def is_mirror(first: TreeNode | None, second: TreeNode | None) -> bool:
    """Return whether `second` is `first` reflected left to right.

    The same recursion as comparing two trees for equality, with the pairs
    crossed: one tree's left subtree must mirror the other's right. Because
    the recursive call is to this function again, the crossing happens at
    every depth -- which is what a reflection is.
    """
    if first is None or second is None:
        return first is second
    return (
        first.value == second.value
        and is_mirror(first.left, second.right)
        and is_mirror(first.right, second.left)
    )
