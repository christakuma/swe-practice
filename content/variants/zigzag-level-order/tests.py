"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import TreeNode, level_order


def from_slots(present: tuple[int, ...]) -> TreeNode | None:
    """A tree from a level-order layout: slot i's children are 2i+1 and 2i+2.

    Each node's value is its slot number, so every value is distinct and says
    where the node sits. A slot whose parent is absent is simply unreachable.
    """
    nodes = [TreeNode(slot) if here else None for slot, here in enumerate(present)]
    for slot, node in enumerate(nodes):
        if node is None:
            continue
        if 2 * slot + 1 < len(nodes):
            node.left = nodes[2 * slot + 1]
        if 2 * slot + 2 < len(nodes):
            node.right = nodes[2 * slot + 2]
    return nodes[0]


def by_depth(root: TreeNode | None) -> list[list[int]]:
    """Depth-first, filing each value under its depth, then flipping odd levels."""
    levels: list[list[int]] = []

    def visit(node: TreeNode | None, depth: int) -> None:
        if node is None:
            return
        if depth == len(levels):
            levels.append([])
        levels[depth].append(node.value)
        visit(node.left, depth + 1)
        visit(node.right, depth + 1)

    visit(root, 0)
    return [level[::-1] if depth % 2 else level for depth, level in enumerate(levels)]


def test_reads_the_second_level_right_to_left() -> None:
    """Reads the second level from right to left."""
    root = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))

    assert level_order(root) == [[3], [20, 9], [15, 7]]


def test_reads_the_third_level_left_to_right_again() -> None:
    """Returns to left-to-right on the third level.

    The level below a reversed one is where reversing the *traversal* shows:
    visiting 3's children before 2's gives 6, 7, 4, 5 here instead of
    4, 5, 6, 7.
    """
    root = TreeNode(
        1,
        TreeNode(2, TreeNode(4), TreeNode(5)),
        TreeNode(3, TreeNode(6), TreeNode(7)),
    )

    assert level_order(root) == [[1], [3, 2], [4, 5, 6, 7]]


def test_alternates_all_the_way_down() -> None:
    """Keeps alternating on the fourth level and below."""
    root = from_slots((1,) * 15)

    assert level_order(root) == [
        [0],
        [2, 1],
        [3, 4, 5, 6],
        [14, 13, 12, 11, 10, 9, 8, 7],
    ]


def test_returns_no_levels_for_an_empty_tree() -> None:
    """Returns an empty list for an empty tree."""
    assert level_order(None) == []


def test_returns_one_level_for_one_node() -> None:
    """Returns one level holding one value."""
    assert level_order(TreeNode(5)) == [[5]]


def test_leaves_no_gap_for_a_missing_child() -> None:
    """Skips absent children rather than recording a placeholder."""
    root = TreeNode(1, TreeNode(2, None, TreeNode(4)), TreeNode(3))

    assert level_order(root) == [[1], [3, 2], [4]]


def test_agrees_with_a_depth_first_grouping_for_every_small_tree() -> None:
    """Matches a depth-first grouping for every tree of up to four levels."""
    for rest in product((0, 1), repeat=14):
        root = from_slots((1, *rest))
        assert level_order(root) == by_depth(root), rest


def test_leaves_the_tree_alone() -> None:
    """Does not rearrange the tree it was given."""
    root = TreeNode(1, TreeNode(2), TreeNode(3))

    level_order(root)

    assert root.left is not None
    assert root.right is not None
    assert (root.left.value, root.right.value) == (2, 3)


def test_reads_a_wide_tree() -> None:
    """Reads a complete tree of fourteen levels.

    The last level holds 8,192 values and is an odd-numbered one, so it comes
    back right to left.
    """
    root = from_slots((1,) * (2**14 - 1))

    levels = level_order(root)

    assert len(levels) == 14
    assert levels[13] == list(range(2**14 - 2, 2**13 - 2, -1))
    assert levels[12] == list(range(2**12 - 1, 2**13 - 1))
