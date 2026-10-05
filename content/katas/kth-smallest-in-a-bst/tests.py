"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from __future__ import annotations

from solution import TreeNode, kth_smallest


def bst(values: list[int]) -> TreeNode | None:
    """Build a balanced BST over `values`, which must be sorted."""
    if not values:
        return None
    middle = len(values) // 2
    return TreeNode(
        values[middle],
        bst(values[:middle]),
        bst(values[middle + 1 :]),
    )


def insert(root: TreeNode | None, value: int) -> TreeNode:
    """Insert into a BST the ordinary way, which may produce a skewed tree."""
    if root is None:
        return TreeNode(value)
    if value < root.value:
        root.left = insert(root.left, value)
    else:
        root.right = insert(root.right, value)
    return root


class Landmine(TreeNode):
    """A node that refuses to be looked at.

    The only way to check an *early exit* from the outside: a tree cannot tell
    you how much of it was read, but a node that raises on access can. Planted
    where a correct solution has no reason to go.
    """

    def __init__(self) -> None:
        """Deliberately uninitialised -- every attribute access raises."""

    @property
    def value(self) -> int:
        raise AssertionError("read a node the answer did not require")

    @property
    def left(self) -> TreeNode | None:
        raise AssertionError("descended past the answer")

    @property
    def right(self) -> TreeNode | None:
        raise AssertionError("descended past the answer")


def test_finds_the_smallest() -> None:
    """Returns the smallest value for k = 1."""
    tree = bst([2, 3, 4, 5, 7, 9])

    assert kth_smallest(tree, 1) == 2


def test_finds_a_middle_value() -> None:
    """Returns the kth smallest for a k in the middle."""
    tree = bst([2, 3, 4, 5, 7, 9])

    assert kth_smallest(tree, 3) == 4


def test_finds_the_largest() -> None:
    """Returns the largest value when k is the tree's size."""
    tree = bst([2, 3, 4, 5, 7, 9])

    assert kth_smallest(tree, 6) == 9


def test_handles_a_single_node() -> None:
    """Returns the only value for a one-node tree."""
    assert kth_smallest(TreeNode(42), 1) == 42


def test_walks_in_order_not_level_order() -> None:
    """Orders by value, not by position in the tree.

    The root is the median, so a solution that visits the root first -- a
    pre-order walk, or a breadth-first one -- returns 5 for k = 1.
    """
    tree = bst([2, 3, 4, 5, 7, 9])

    assert kth_smallest(tree, 1) != tree.value
    assert kth_smallest(tree, 1) == 2


def test_finds_every_k_in_order() -> None:
    """Returns the values in sorted order as k increases."""
    values = [1, 4, 9, 16, 25, 36, 49, 64, 81]
    tree = bst(values)

    assert [kth_smallest(tree, k) for k in range(1, len(values) + 1)] == values


def test_handles_a_left_skewed_tree() -> None:
    """Handles a tree that is effectively a descending linked list."""
    tree = None
    for value in (5, 4, 3, 2, 1):
        tree = insert(tree, value)

    assert [kth_smallest(tree, k) for k in range(1, 6)] == [1, 2, 3, 4, 5]


def test_handles_a_right_skewed_tree() -> None:
    """Handles a tree that is effectively an ascending linked list."""
    tree = None
    for value in (1, 2, 3, 4, 5):
        tree = insert(tree, value)

    assert [kth_smallest(tree, k) for k in range(1, 6)] == [1, 2, 3, 4, 5]


def test_handles_negative_values() -> None:
    """Orders negative values correctly."""
    tree = bst([-9, -4, -1, 0, 3])

    assert [kth_smallest(tree, k) for k in range(1, 6)] == [-9, -4, -1, 0, 3]


def test_stops_as_soon_as_it_has_the_answer() -> None:
    """Does not read nodes beyond the kth.

    The root's right subtree holds everything larger than the root, so for
    k = 1 there is no reason to touch it. Collecting every value and indexing
    -- correct, O(n) time and O(n) space -- trips the landmine here.
    """
    tree = bst([1, 2, 3])
    tree.right = Landmine()

    assert kth_smallest(tree, 1) == 1


def test_stops_after_the_kth_in_a_larger_tree() -> None:
    """Reads only the left spine and k nodes, not the whole tree."""
    tree = bst(list(range(1, 32)))
    tree.right = Landmine()

    assert kth_smallest(tree, 1) == 1
    assert kth_smallest(tree, 8) == 8
    assert kth_smallest(tree, 16) == 16


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a node."""
    assert type(kth_smallest(TreeNode(1), 1)) is int


def test_agrees_with_sorting_across_every_balanced_size() -> None:
    """Matches the sorted values for every k, at every size up to sixty.

    The traversal is the only thing that establishes the ordering, so an
    off-by-one in the counter or a left/right swap shows up as a consistent
    shift that a single spot check can miss.
    """
    for size in range(1, 61):
        values = [value * 7 - 13 for value in range(size)]
        tree = bst(values)

        for k in range(1, size + 1):
            assert kth_smallest(tree, k) == values[k - 1], (size, k)


def test_handles_a_large_tree() -> None:
    """Finds a value in a tree of a hundred thousand nodes."""
    values = list(range(100_000))
    tree = bst(values)

    assert kth_smallest(tree, 1) == 0
    assert kth_smallest(tree, 50_000) == 49_999
    assert kth_smallest(tree, 100_000) == 99_999
