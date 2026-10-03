"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import TreeNode, lowest_common_ancestor


def build() -> TreeNode:
    r"""The tree every test below uses.

                3
             /     \
            5       1
          /   \    /  \
         6     2  0    8
              / \
             7   4
    """
    return TreeNode(
        3,
        TreeNode(5, TreeNode(6), TreeNode(2, TreeNode(7), TreeNode(4))),
        TreeNode(1, TreeNode(0), TreeNode(8)),
    )


def test_finds_an_ancestor_across_the_root() -> None:
    """Finds the root when the two values are on opposite sides."""
    assert lowest_common_ancestor(build(), 5, 1) == 3


def test_finds_the_deepest_ancestor_not_just_any_one() -> None:
    """Returns the deepest common ancestor, not the root.

    3 is a common ancestor of 7 and 4 and so is 5; the answer is 2. A solution
    that returns the first node with both values below it, from the top down,
    says 3.
    """
    assert lowest_common_ancestor(build(), 7, 4) == 2


def test_treats_a_node_as_its_own_ancestor() -> None:
    """Returns the higher node when one value is an ancestor of the other."""
    assert lowest_common_ancestor(build(), 5, 4) == 5


def test_handles_the_two_values_in_either_order() -> None:
    """Gives the same answer whichever way round the values are given."""
    assert lowest_common_ancestor(build(), 4, 5) == 5


def test_finds_an_ancestor_deep_on_one_side() -> None:
    """Finds an ancestor that is not on the path to the root."""
    assert lowest_common_ancestor(build(), 6, 4) == 5


def test_handles_both_values_being_the_same_node() -> None:
    """Returns the node itself when both values are the same."""
    assert lowest_common_ancestor(build(), 7, 7) == 7


def test_returns_nothing_when_a_value_is_missing() -> None:
    """Refuses rather than guessing when a value is not in the tree.

    A solution without a presence check returns 5 here -- the position of the
    value it did find -- which is a confident wrong answer.
    """
    assert lowest_common_ancestor(build(), 5, 99) is None


def test_returns_nothing_for_an_empty_tree() -> None:
    """Returns None when there is no tree."""
    assert lowest_common_ancestor(None, 1, 2) is None


def test_handles_a_single_node_tree() -> None:
    """Returns the only node when both values are it."""
    assert lowest_common_ancestor(TreeNode(9), 9, 9) == 9
