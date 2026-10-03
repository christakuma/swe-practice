"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import TreeNode, is_search_tree


def test_accepts_a_valid_search_tree() -> None:
    """Accepts a tree where every subtree is in range."""
    tree = TreeNode(2, TreeNode(1), TreeNode(3))

    assert is_search_tree(tree) is True


def test_rejects_a_child_out_of_order() -> None:
    """Rejects a node whose immediate child is on the wrong side."""
    tree = TreeNode(5, TreeNode(6), TreeNode(7))

    assert is_search_tree(tree) is False


def test_rejects_a_distant_descendant_out_of_range() -> None:
    """Rejects a value that is fine for its parent and wrong for an ancestor.

    The whole point of the kata. 6 is a legitimate right child of 3, and 3 is a
    legitimate left child of 5 -- but 6 sits in 5's left subtree, where
    everything must be below 5. A solution that compares each node only against
    its own children says yes.
    """
    tree = TreeNode(5, TreeNode(3, TreeNode(1), TreeNode(6)), TreeNode(8))

    assert is_search_tree(tree) is False


def test_rejects_a_duplicate_of_an_ancestor() -> None:
    """Rejects a repeated value: the ordering here is strict."""
    tree = TreeNode(2, TreeNode(2), TreeNode(3))

    assert is_search_tree(tree) is False


def test_accepts_an_empty_tree() -> None:
    """Accepts an empty tree."""
    assert is_search_tree(None) is True


def test_accepts_a_single_node() -> None:
    """Accepts a tree of one node."""
    assert is_search_tree(TreeNode(42)) is True


def test_accepts_a_tree_that_leans_right() -> None:
    """Accepts a valid chain that only ever goes right."""
    tree = TreeNode(1, None, TreeNode(2, None, TreeNode(3)))

    assert is_search_tree(tree) is True


def test_rejects_a_chain_that_turns_back() -> None:
    """Rejects a right-leaning chain whose last value drops below the root."""
    tree = TreeNode(10, None, TreeNode(20, TreeNode(5)))

    assert is_search_tree(tree) is False


def test_handles_negative_values() -> None:
    """Accepts negative values, which bound-based solutions must not assume away.

    A solution seeded with 0 as its lower bound, rather than with no bound at
    all, rejects this valid tree.
    """
    tree = TreeNode(0, TreeNode(-10), TreeNode(5))

    assert is_search_tree(tree) is True


def test_handles_a_deep_valid_chain() -> None:
    """Validates a chain deep enough to be worth a thought about the stack."""
    depth = 500
    root = TreeNode(0)
    node = root
    for value in range(1, depth):
        node.right = TreeNode(value)
        node = node.right

    assert is_search_tree(root) is True
