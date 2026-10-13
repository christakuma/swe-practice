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


def rebuild(inorder: list[int], postorder: list[int]) -> TreeNode | None:
    """Rebuild the tree from its in-order and post-order traversals.

    Post-order read backwards is root, right subtree, left subtree. So a
    single index walks it from the end, each call taking the next value as
    its root, and the right subtree is built before the left -- that is the
    order the values arrive in.

    `position` turns "where is this root in the in-order list" from a scan
    into a lookup, which is what keeps the whole thing linear.
    """
    position = {value: index for index, value in enumerate(inorder)}
    at = len(postorder) - 1

    def build(low: int, high: int) -> TreeNode | None:
        nonlocal at
        if low > high:
            return None
        value = postorder[at]
        at -= 1
        middle = position[value]
        right = build(middle + 1, high)
        left = build(low, middle - 1)
        return TreeNode(value, left, right)

    return build(0, len(inorder) - 1)
