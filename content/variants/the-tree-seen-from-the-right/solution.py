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


def right_side_view(root: TreeNode | None) -> list[int]:
    """Return the rightmost value on each level, top to bottom.

    The level-order traversal with most of its output discarded. Each round
    holds one complete level, in left-to-right order, and builds the next
    from it; the value kept is the level's last.

    Working a level at a time is what makes "rightmost" well defined. It is a
    statement about a whole level, and a node in the left subtree qualifies
    whenever nothing further right reaches that depth.
    """
    seen: list[int] = []
    level = [root] if root is not None else []
    while level:
        seen.append(level[-1].value)
        level = [
            child
            for node in level
            for child in (node.left, node.right)
            if child is not None
        ]
    return seen
