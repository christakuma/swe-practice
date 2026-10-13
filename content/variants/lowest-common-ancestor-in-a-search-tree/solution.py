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


def lowest_common_ancestor(root: TreeNode | None, first: int, second: int) -> int:
    """Return the value of the deepest node with both values at or below it.

    The ordering says where everything is, so there is nothing to search.
    While both values are on the same side of the current node, that is the
    side the answer is on. The first node they are *not* both to one side of
    is where the two paths from the root diverge -- or is one of the values
    itself -- and either way it is the lowest node above both.

    A loop, and deliberately not a recursive search of the whole tree: only
    the nodes on one root-to-answer path are ever touched.
    """
    low, high = min(first, second), max(first, second)
    node = root
    while node is not None:
        if high < node.value:
            node = node.left
        elif low > node.value:
            node = node.right
        else:
            return node.value
    raise ValueError("both values must be in the tree")
