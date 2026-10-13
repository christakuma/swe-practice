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


def kth_largest(root: TreeNode | None, k: int) -> int:
    """Return the kth largest value in the BST, 1-based.

    A reverse in-order walk -- right, node, left -- visits the values in
    descending order, so the kth node visited is the answer. An explicit
    stack makes stopping there trivial: the walk simply returns, having
    touched the right spine and k nodes and nothing else. In particular it
    never descends into a left subtree it does not need.
    """
    stack: list[TreeNode] = []
    node = root
    while True:
        while node is not None:
            stack.append(node)
            node = node.right
        node = stack.pop()
        k -= 1
        if k == 0:
            return node.value
        node = node.left
