"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import TreeNode, kth_largest


def balanced(values: list[int]) -> TreeNode | None:
    """A balanced BST over sorted values."""
    if not values:
        return None
    middle = len(values) // 2
    return TreeNode(
        values[middle], balanced(values[:middle]), balanced(values[middle + 1 :])
    )


def example() -> TreeNode:
    return TreeNode(
        5, TreeNode(3, TreeNode(2), TreeNode(4)), TreeNode(7, None, TreeNode(9))
    )


def test_returns_the_largest_for_k_of_one() -> None:
    """Returns the largest value for k = 1."""
    assert kth_largest(example(), 1) == 9


def test_counts_down_from_the_largest() -> None:
    """Returns the values in descending order as k increases."""
    assert [kth_largest(example(), k) for k in range(1, 7)] == [9, 7, 5, 4, 3, 2]


def test_handles_a_single_node() -> None:
    """Returns the only value of a one-node tree."""
    assert kth_largest(TreeNode(8), 1) == 8


def test_handles_chains_in_both_directions() -> None:
    """Handles trees that lean entirely one way."""
    rising = TreeNode(1, None, TreeNode(2, None, TreeNode(3)))
    falling = TreeNode(3, TreeNode(2, TreeNode(1)))

    assert [kth_largest(rising, k) for k in (1, 2, 3)] == [3, 2, 1]
    assert [kth_largest(falling, k) for k in (1, 2, 3)] == [3, 2, 1]


def test_agrees_with_sorting_at_every_size() -> None:
    """Matches the sorted values for every k, at every size up to sixty."""
    for size in range(1, 61):
        values = list(range(-size, 2 * size, 3))
        tree = balanced(values)
        for k in range(1, len(values) + 1):
            assert kth_largest(tree, k) == values[-k], (size, k)


def test_does_not_walk_a_deep_left_side_it_does_not_need() -> None:
    """Answers from the right of a tree whose left is a chain 100,000 deep.

    The three largest values are all in the small right subtree, so nothing
    on the left needs visiting. A walk that collects every value first
    recurses down the chain and runs out of stack.
    """
    top = 1_000_000
    chain = TreeNode(top - 1)
    node = chain
    for value in range(top - 2, top - 100_001, -1):
        node.left = TreeNode(value)
        node = node.left
    root = TreeNode(top, chain, TreeNode(top + 5, TreeNode(top + 2), TreeNode(top + 9)))

    assert [kth_largest(root, k) for k in (1, 2, 3, 4)] == [
        top + 9,
        top + 5,
        top + 2,
        top,
    ]


def test_finds_a_value_in_a_large_tree() -> None:
    """Finds values in a balanced tree of a hundred thousand nodes."""
    values = list(range(100_000))
    tree = balanced(values)

    assert kth_largest(tree, 1) == 99_999
    assert kth_largest(tree, 50_000) == 50_000
