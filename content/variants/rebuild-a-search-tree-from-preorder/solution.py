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


def rebuild(preorder: list[int]) -> TreeNode | None:
    """Rebuild a binary search tree from its pre-order traversal.

    `path` is a stack holding the nodes from the root down to the node just
    placed, restricted to those whose right child is still unset. Its values
    decrease from bottom to top.

    Each new value is attached in one of two ways. Smaller than the top: it
    is the top's left child, because pre-order goes left immediately after a
    node. Larger: every node on the stack that it exceeds has a finished left
    side and cannot be its ancestor on the left, so they are popped, and the
    value becomes the right child of the last one popped -- the deepest node
    it is larger than.

    Every node is pushed once and popped at most once, so the whole build is
    linear, and nothing recurses, so a chain of any depth is fine.
    """
    if not preorder:
        return None
    root = TreeNode(preorder[0])
    path = [root]
    for value in preorder[1:]:
        node = TreeNode(value)
        if value < path[-1].value:
            path[-1].left = node
        else:
            parent = path.pop()
            while path and path[-1].value < value:
                parent = path.pop()
            parent.right = node
        path.append(node)
    return root
