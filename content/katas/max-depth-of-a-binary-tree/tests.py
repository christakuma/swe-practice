"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import TreeNode, max_depth


def test_measures_a_small_tree() -> None:
    """Returns the depth of the longest root-to-leaf path."""
    tree = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))

    assert max_depth(tree) == 3


def test_handles_an_empty_tree() -> None:
    """Returns zero for an empty tree."""
    assert max_depth(None) == 0


def test_handles_a_single_node() -> None:
    """Returns one for a tree of one node."""
    assert max_depth(TreeNode(1)) == 1


def test_takes_the_deeper_of_two_unbalanced_subtrees() -> None:
    """Returns the deeper side, not the first one it looked at.

    The left subtree is one node and the right is three. A solution that
    recurses into only one side, or adds the two depths, is wrong here and
    right on a balanced tree.
    """
    tree = TreeNode(
        1,
        TreeNode(2),
        TreeNode(3, TreeNode(4, TreeNode(5))),
    )

    assert max_depth(tree) == 4


def test_handles_a_tree_that_leans_left() -> None:
    """Measures a chain that only ever goes left."""
    tree = TreeNode(1, TreeNode(2, TreeNode(3)))

    assert max_depth(tree) == 3


def test_does_not_count_missing_children() -> None:
    """Counts nodes on the path, not the slots where children could be."""
    tree = TreeNode(1, TreeNode(2, None, TreeNode(3)))

    assert max_depth(tree) == 3


def test_handles_a_deep_chain() -> None:
    """Measures a chain deep enough to be worth thinking about the stack.

    Five hundred nodes in a line. Python's default recursion limit is 1000
    frames, so a recursive solution survives this and a tree twice as deep
    would raise RecursionError -- which is a real constraint and not a bug in
    the algorithm.
    """
    depth = 500
    root = TreeNode(0)
    node = root
    for value in range(1, depth):
        node.left = TreeNode(value)
        node = node.left

    assert max_depth(root) == depth
