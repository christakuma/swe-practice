"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations

import heapq
from itertools import islice
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


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


def _ascending(root: TreeNode | None) -> Iterator[int]:
    """The tree's values in ascending order, produced one at a time."""
    stack: list[TreeNode] = []
    node = root
    while stack or node is not None:
        while node is not None:
            stack.append(node)
            node = node.left
        node = stack.pop()
        yield node.value
        node = node.right


def kth_smallest(first: TreeNode | None, second: TreeNode | None, k: int) -> int:
    """Return the kth smallest value across two BSTs, 1-based.

    An in-order walk of a search tree is an ascending sequence, so two trees
    are two ascending sequences and the question is the kth value of their
    merge. Nothing is materialised: each walk is a generator that descends
    only as far as its next value needs, `heapq.merge` draws from whichever
    has the smaller front, and `islice` stops the whole thing at the kth.

    A value present in both trees comes out of both generators, so it is
    counted twice without any special handling.
    """
    merged = heapq.merge(_ascending(first), _ascending(second))
    return next(islice(merged, k - 1, None))
