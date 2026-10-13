"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator

from solution import TreeNode, right_side_view

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


def by_paths(root: TreeNode | None) -> list[int]:
    """Label every node with its path from the root and take the last per depth.

    With "L" sorting before "R", the greatest path of a given length is the
    rightmost node on that level.
    """
    last: dict[int, tuple[str, int]] = {}
    pending = [(root, "")]
    while pending:
        node, path = pending.pop()
        if node is None:
            continue
        if len(path) not in last or path > last[len(path)][0]:
            last[len(path)] = (path, node.value)
        pending.append((node.left, path + "L"))
        pending.append((node.right, path + "R"))
    return [last[depth][1] for depth in sorted(last)]


def test_sees_the_right_hand_node_of_each_level() -> None:
    """Returns the last value on each level of a bushy tree."""
    root = TreeNode(1, TreeNode(2, None, TreeNode(5)), TreeNode(3, None, TreeNode(4)))

    assert right_side_view(root) == [1, 3, 4]


def test_sees_into_the_left_subtree_where_the_right_is_shorter() -> None:
    """Returns a node from the left subtree when nothing to its right is as deep."""
    root = TreeNode(1, TreeNode(2, TreeNode(4)), TreeNode(3))
    deeper = TreeNode(
        1, TreeNode(2, TreeNode(4, None, TreeNode(6))), TreeNode(3, TreeNode(5))
    )

    assert right_side_view(root) == [1, 3, 4]
    assert right_side_view(deeper) == [1, 3, 5, 6]


def test_a_tree_that_only_goes_left_is_all_visible() -> None:
    """Returns every value of a left-leaning chain."""
    assert right_side_view(TreeNode(1, TreeNode(2, TreeNode(3)))) == [1, 2, 3]


def test_a_tree_that_only_goes_right_is_all_visible() -> None:
    """Returns every value of a right-leaning chain."""
    assert right_side_view(TreeNode(1, None, TreeNode(2, None, TreeNode(3)))) == [
        1,
        2,
        3,
    ]


def test_prefers_a_right_child_to_a_left_child() -> None:
    """Returns the right child of two siblings, and the right cousin of two cousins."""
    assert right_side_view(TreeNode(1, TreeNode(2), TreeNode(3))) == [1, 3]
    cousins = TreeNode(
        1, TreeNode(2, TreeNode(4), None), TreeNode(3, TreeNode(5), None)
    )
    assert right_side_view(cousins) == [1, 3, 5]


def test_handles_an_empty_tree_and_a_single_node() -> None:
    """Returns [] for no tree and one value for a tree of one node."""
    assert right_side_view(None) == []
    assert right_side_view(TreeNode(7)) == [7]


def test_values_may_repeat() -> None:
    """Chooses by position, not by value."""
    root = TreeNode(5, TreeNode(5, TreeNode(9)), TreeNode(5))

    assert right_side_view(root) == [5, 5, 9]


def test_agrees_with_labelling_every_node_by_its_path() -> None:
    """Matches a path-labelling search for every tree shape of up to eight nodes."""
    for size in range(9):
        for shape in shapes(size):
            tree = grow(shape, iter(range(size)))
            assert right_side_view(tree) == by_paths(tree), shape


def test_leaves_the_tree_alone() -> None:
    """Does not modify the tree."""
    root = TreeNode(1, TreeNode(2), TreeNode(3))

    right_side_view(root)

    assert (root.left.value, root.right.value) == (2, 3)


def test_handles_a_very_deep_chain() -> None:
    """Handles a zigzag chain of twenty thousand nodes without recursing."""
    root = TreeNode(0)
    node = root
    for value in range(1, 20_000):
        child = TreeNode(value)
        if value % 3:
            node.left = child
        else:
            node.right = child
        node = child

    assert right_side_view(root) == list(range(20_000))


def test_handles_a_wide_tree() -> None:
    """Handles a full tree of over sixteen thousand nodes."""

    def full(depth: int, value: int) -> TreeNode:
        if depth == 0:
            return TreeNode(value)
        return TreeNode(
            value, full(depth - 1, 2 * value), full(depth - 1, 2 * value + 1)
        )

    assert right_side_view(full(13, 1)) == [2**level - 1 for level in range(1, 15)]
