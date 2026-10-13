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


def serialize(root: TreeNode | None) -> str:
    """Turn a binary search tree into a string of its values.

    Pre-order: a node, then its left subtree, then its right. With the search
    property that order is enough to recover the shape, because the values
    following a node divide into "smaller, so on its left" and "larger, so on
    its right" with no marker needed between them.
    """
    values: list[str] = []
    pending = [root] if root is not None else []
    while pending:
        node = pending.pop()
        values.append(str(node.value))
        if node.right is not None:
            pending.append(node.right)
        if node.left is not None:
            pending.append(node.left)
    return ",".join(values)


def deserialize(data: str) -> TreeNode | None:
    """Rebuild the tree that `serialize` was given.

    The pre-order rebuild for a search tree. `path` holds the nodes on the
    way down whose right child is still open, largest at the bottom. A value
    smaller than the top goes to its left. A larger one closes every node it
    exceeds and becomes the right child of the last of them.
    """
    if not data:
        return None
    values = [int(part) for part in data.split(",")]
    root = TreeNode(values[0])
    path = [root]
    for value in values[1:]:
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
