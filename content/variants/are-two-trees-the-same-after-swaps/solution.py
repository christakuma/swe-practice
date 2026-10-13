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


def is_same_tree(first: TreeNode | None, second: TreeNode | None) -> bool:
    """Return whether swapping children at some nodes makes the trees equal.

    The standard recursion with a second way for the children to pair up. A
    swap at this node exchanges `second`'s subtrees, so the trees match if the
    roots do and either the children match straight across or they match
    crossed over.

    Each alternative is one whole pairing joined by `and`. Writing it as "the
    left child matches one of theirs, and the right child matches one of
    theirs" lets both of ours claim the same one of theirs.
    """
    if first is None or second is None:
        return first is second
    if first.value != second.value:
        return False
    straight = is_same_tree(first.left, second.left) and is_same_tree(
        first.right, second.right
    )
    return straight or (
        is_same_tree(first.left, second.right)
        and is_same_tree(first.right, second.left)
    )
