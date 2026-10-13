"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class TreeNode:
    """A binary tree node that knows its parent."""

    def __init__(self, value: int, parent: TreeNode | None = None) -> None:
        self.value = value
        self.parent = parent
        self.left: TreeNode | None = None
        self.right: TreeNode | None = None


def lowest_common_ancestor(first: TreeNode, second: TreeNode) -> TreeNode:
    """Return the deepest node with both given nodes at or below it.

    Following `parent` from a node traces a chain up to the root, so the two
    nodes are the heads of two linked lists that merge, and the answer is
    where they merge.

    Two pointers climb one step at a time. When either runs off the top it
    restarts from the *other* node. By the time each has climbed its own
    chain and then the other's, both have taken the same number of steps --
    which lines them up exactly as far below the join as each other. They
    meet there, or sooner if the chains were the same length to begin with.

    They always do meet, because both nodes are in one tree and share at
    least the root.
    """
    a, b = first, second
    while a is not b:
        a = a.parent if a is not None else second
        b = b.parent if b is not None else first
    return a
