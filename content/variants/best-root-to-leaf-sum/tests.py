"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator
from itertools import product

from solution import TreeNode, best_path_sum

type Shape = tuple["Shape", "Shape"] | None


def shapes(size: int) -> Iterator[Shape]:
    """Every binary tree shape with `size` nodes."""
    if size == 0:
        yield None
        return
    for on_left in range(size):
        for left in shapes(on_left):
            for right in shapes(size - 1 - on_left):
                yield (left, right)


def grow(shape: Shape, values: Iterator[int]) -> TreeNode | None:
    """A tree of the given shape, filled with values in pre-order."""
    if shape is None:
        return None
    value = next(values)
    return TreeNode(value, grow(shape[0], values), grow(shape[1], values))


def leaf_sums(root: TreeNode) -> list[int]:
    """The total of every root-to-leaf path, found with an explicit stack."""
    totals = []
    stack = [(root, root.value)]
    while stack:
        node, total = stack.pop()
        children = [child for child in (node.left, node.right) if child is not None]
        if not children:
            totals.append(total)
        for child in children:
            stack.append((child, total + child.value))
    return totals


def test_picks_the_better_of_two_leaves() -> None:
    """Follows the child that leads to the larger total."""
    assert best_path_sum(TreeNode(1, TreeNode(2), TreeNode(3))) == 4
    assert best_path_sum(TreeNode(1, TreeNode(9), TreeNode(3))) == 10


def test_a_single_node_is_its_own_path() -> None:
    """Returns the value of a tree that is only a root."""
    assert best_path_sum(TreeNode(8)) == 8
    assert best_path_sum(TreeNode(-7)) == -7


def test_does_not_turn_at_the_root() -> None:
    """Counts one side of the root, never both."""
    root = TreeNode(-10, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))

    assert best_path_sum(root) == 25


def test_does_not_stop_above_a_negative_leaf() -> None:
    """Goes on to the leaf even when stopping earlier would score more."""
    assert best_path_sum(TreeNode(10, TreeNode(-5))) == 5
    assert best_path_sum(TreeNode(10, None, TreeNode(3, TreeNode(-8)))) == 5


def test_a_missing_child_is_not_a_path_worth_nothing() -> None:
    """Takes the only way down from a node with one child, however bad it is."""
    root = TreeNode(5, TreeNode(4, TreeNode(-20)), TreeNode(1, None, TreeNode(2)))

    assert best_path_sum(root) == 8
    assert best_path_sum(TreeNode(1, TreeNode(-3))) == -2
    assert best_path_sum(TreeNode(1, None, TreeNode(-3))) == -2


def test_handles_a_tree_of_negatives() -> None:
    """Returns the least bad path when every value is negative."""
    root = TreeNode(-1, TreeNode(-2, TreeNode(-4)), TreeNode(-3))

    assert best_path_sum(root) == -4


def test_does_not_start_below_the_root() -> None:
    """Includes the root's value even when it is a large loss."""
    root = TreeNode(-100, TreeNode(50), TreeNode(60))

    assert best_path_sum(root) == -40


def test_agrees_with_listing_every_path_on_every_small_tree() -> None:
    """Matches the best of all root-to-leaf totals for every small tree.

    Every shape of one to five nodes, with every value drawn from -3, 1, 2.
    """
    checked = 0
    for size in range(1, 6):
        for shape in shapes(size):
            for values in product((-3, 1, 2), repeat=size):
                tree = grow(shape, iter(values))
                assert tree is not None
                assert best_path_sum(tree) == max(leaf_sums(tree)), (shape, values)
                checked += 1
    assert checked > 10_000


def test_walks_a_wide_tree() -> None:
    """Handles a balanced tree of over eight thousand nodes."""

    def full(depth: int, value: int) -> TreeNode:
        if depth == 0:
            return TreeNode(value)
        return TreeNode(value, full(depth - 1, value - 1), full(depth - 1, value + 1))

    assert best_path_sum(full(12, 0)) == sum(range(13))
