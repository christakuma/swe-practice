"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import TreeNode, level_order


def test_groups_a_small_tree_by_level() -> None:
    """Returns one list per level, top to bottom."""
    tree = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))

    assert level_order(tree) == [[3], [9, 20], [15, 7]]


def test_orders_each_level_left_to_right() -> None:
    """Reads each level from left to right."""
    tree = TreeNode(1, TreeNode(2, TreeNode(4), TreeNode(5)), TreeNode(3))

    assert level_order(tree) == [[1], [2, 3], [4, 5]]


def test_handles_an_empty_tree() -> None:
    """Returns no levels for an empty tree."""
    assert level_order(None) == []


def test_handles_a_single_node() -> None:
    """Returns one level of one value."""
    assert level_order(TreeNode(1)) == [[1]]


def test_does_not_leave_a_gap_for_a_missing_child() -> None:
    """Skips absent children rather than recording a placeholder.

    The right child of 2 is missing, so level 2 holds one value and not two.
    """
    tree = TreeNode(1, TreeNode(2, TreeNode(4)), TreeNode(3))

    assert level_order(tree) == [[1], [2, 3], [4]]


def test_keeps_levels_separate_in_a_lopsided_tree() -> None:
    """Puts each value on its own level in a chain.

    A solution that collects every node in breadth-first order and then guesses
    the level boundaries by counting 1, 2, 4, 8 gets this wrong from level 2 on.
    """
    tree = TreeNode(1, TreeNode(2, TreeNode(3, TreeNode(4))))

    assert level_order(tree) == [[1], [2], [3], [4]]


def test_handles_a_full_tree() -> None:
    """Handles a tree where every level is complete."""
    tree = TreeNode(
        1,
        TreeNode(2, TreeNode(4), TreeNode(5)),
        TreeNode(3, TreeNode(6), TreeNode(7)),
    )

    assert level_order(tree) == [[1], [2, 3], [4, 5, 6, 7]]


def test_handles_a_wide_tree_quickly() -> None:
    """Traverses a tree wide enough to punish a list used as a queue.

    A complete tree of depth 14 -- about sixteen thousand nodes, half of them
    on the last level. `list.pop(0)` shifts the whole queue on every node,
    which is quadratic in the width of the widest level.
    """
    depth = 14
    nodes = [TreeNode(0) for _ in range(2**depth - 1)]
    for index in range(len(nodes)):
        left, right = 2 * index + 1, 2 * index + 2
        if left < len(nodes):
            nodes[index].left = nodes[left]
        if right < len(nodes):
            nodes[index].right = nodes[right]

    levels = level_order(nodes[0])

    assert len(levels) == depth
    assert len(levels[-1]) == 2 ** (depth - 1)
