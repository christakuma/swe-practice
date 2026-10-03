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
    """Whether the tree satisfies the binary search tree property.

    The trap this kata exists for: checking each node against its own children
    is not the property. `TreeNode(5, TreeNode(1, None, TreeNode(6)), ...)` has
    every parent-child pair in order and a 6 in the left subtree of a 5, so it
    is not a search tree. The constraint is on every *descendant*, not on
    children.

    Which means each node needs to know the window it is allowed to be in, and
    that window narrows as you descend: going left caps the maximum at this
    node's value, going right raises the minimum to it. The bounds are the state
    the recursion carries, and carrying them is what turns a local check into a
    global one.

    `None` for an absent bound rather than a sentinel like negative infinity:
    float("-inf") compares fine against ints and is a lie about the type, and
    this way the only values compared are the ones in the tree.
    """

    def within(node: TreeNode | None, low: int | None, high: int | None) -> bool:
        if node is None:
            return True
        if low is not None and node.value <= low:
            return False
        if high is not None and node.value >= high:
            return False
        return within(node.left, low, node.value) and within(
            node.right, node.value, high
        )

    return within(root, None, None)
