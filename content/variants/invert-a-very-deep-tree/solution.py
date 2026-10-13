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


def invert(root: TreeNode | None) -> TreeNode | None:
    """Mirror the tree in place and return its root.

    The recursive version's call stack is a list of nodes still to visit.
    Here the list is explicit, which moves it from the interpreter's stack --
    about a thousand frames -- to the heap, where a hundred thousand entries
    are nothing.

    Any visiting order works, because swapping one node's children does not
    depend on any other node having been done. A list used as a stack is the
    simplest; on a chain it never holds more than one node.
    """
    pending = [root] if root is not None else []
    while pending:
        node = pending.pop()
        node.left, node.right = node.right, node.left
        if node.left is not None:
            pending.append(node.left)
        if node.right is not None:
            pending.append(node.right)
    return root
