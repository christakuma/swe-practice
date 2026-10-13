"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator
from itertools import combinations

from solution import TreeNode, swapped_values

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


def fill(shape: Shape, values: Iterator[int]) -> TreeNode | None:
    """A tree of this shape whose in-order traversal is `values`."""
    if shape is None:
        return None
    left = fill(shape[0], values)
    node = TreeNode(next(values), left)
    node.right = fill(shape[1], values)
    return node


def with_swap(shape: Shape, size: int, first: int, second: int) -> TreeNode | None:
    """The search tree of this shape on 10, 20, ..., with two positions exchanged."""
    values = [10 * (index + 1) for index in range(size)]
    values[first], values[second] = values[second], values[first]
    return fill(shape, iter(values))


def test_finds_a_swapped_parent_and_child() -> None:
    """Finds two exchanged values that are directly joined."""
    assert swapped_values(TreeNode(1, TreeNode(2), TreeNode(3))) == (1, 2)
    assert swapped_values(TreeNode(3, TreeNode(1), TreeNode(2))) == (2, 3)


def test_finds_values_swapped_across_the_tree() -> None:
    """Finds two exchanged values in different subtrees.

    The tree should read 1, 2, 3, 4, 5 in order and reads 1, 4, 3, 2, 5. Both
    misplaced nodes are leaves, and each still compares correctly with its
    own parent's neighbours on one side.
    """
    root = TreeNode(3, TreeNode(1, None, TreeNode(4)), TreeNode(5, TreeNode(2)))

    assert swapped_values(root) == (2, 4)


def test_returns_none_for_a_valid_tree() -> None:
    """Returns None when nothing has been exchanged."""
    assert swapped_values(TreeNode(2, TreeNode(1), TreeNode(3))) is None
    assert swapped_values(TreeNode(7)) is None
    assert swapped_values(None) is None


def test_returns_the_smaller_value_first() -> None:
    """Orders the pair by value, wherever the two nodes are."""
    assert swapped_values(TreeNode(1, TreeNode(3, None, TreeNode(2)))) == (1, 3)
    assert swapped_values(TreeNode(5, None, TreeNode(2))) == (2, 5)
    assert swapped_values(TreeNode(2, TreeNode(5))) == (2, 5)


def test_finds_the_first_and_last_values_swapped() -> None:
    """Finds an exchange of the smallest and largest values."""
    root = TreeNode(20, TreeNode(40), TreeNode(30, None, TreeNode(10)))

    assert swapped_values(root) == (10, 40)


def test_neighbours_in_order_need_not_be_neighbours_in_the_tree() -> None:
    """Finds a single drop whose two values are far apart in the tree."""
    root = TreeNode(3, TreeNode(1), TreeNode(4, TreeNode(2)))

    assert swapped_values(root) == (2, 3)


def test_handles_negative_values() -> None:
    """Handles values below zero."""
    root = TreeNode(0, TreeNode(5), TreeNode(-5))

    assert swapped_values(root) == (-5, 5)


def test_finds_every_swap_in_every_small_tree() -> None:
    """Finds the pair for every shape of up to six nodes and every two positions."""
    for size in range(2, 7):
        for shape in shapes(size):
            assert swapped_values(with_swap(shape, size, 0, 0)) is None, shape
            for first, second in combinations(range(size), 2):
                tree = with_swap(shape, size, first, second)
                expected = (10 * (first + 1), 10 * (second + 1))
                assert swapped_values(tree) == expected, (shape, first, second)


def test_leaves_the_tree_alone() -> None:
    """Reports the swap without undoing it."""
    root = TreeNode(1, TreeNode(2), TreeNode(3))

    swapped_values(root)

    assert (root.value, root.left.value, root.right.value) == (1, 2, 3)


def test_handles_a_very_deep_tree() -> None:
    """Handles a chain of ten thousand nodes without recursing."""
    size = 10_000
    values = list(range(size))
    values[17], values[9_000] = values[9_000], values[17]
    root = None
    for value in reversed(values):
        root = TreeNode(value, None, root)

    assert swapped_values(root) == (17, 9_000)


def test_handles_a_large_bushy_tree() -> None:
    """Finds a swap of two leaves on opposite sides of ten thousand nodes."""

    def balanced(low: int, high: int) -> TreeNode | None:
        if low >= high:
            return None
        middle = (low + high) // 2
        return TreeNode(middle, balanced(low, middle), balanced(middle + 1, high))

    root = balanced(0, 10_000)
    assert swapped_values(root) is None

    left = right = root
    while left.left is not None:
        left = left.left
    while right.right is not None:
        right = right.right
    left.value, right.value = right.value, left.value

    assert swapped_values(root) == (0, 9_999)
