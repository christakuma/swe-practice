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


def is_search_tree(root: TreeNode | None) -> bool:
    """Whether the tree is a search tree that allows repeats on the left.

    Each node must lie in a range inherited from its ancestors: strictly
    above `above`, and at or below `at_most`. Going left tightens the upper
    bound to the node's value, inclusively -- an equal value is welcome
    there. Going right tightens the lower bound to it, exclusively.

    The asymmetry is the whole of the difference from the strict version,
    and it is carried by the bounds rather than by comparing a child with
    its parent, because a repeat may be many levels below the value it
    repeats.
    """

    def within(node: TreeNode | None, above: float, at_most: float) -> bool:
        if node is None:
            return True
        if not above < node.value <= at_most:
            return False
        return within(node.left, above, node.value) and within(
            node.right, node.value, at_most
        )

    return within(root, float("-inf"), float("inf"))
