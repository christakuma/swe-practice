"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator

from solution import TreeNode, is_balanced

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


def grow(shape: Shape) -> TreeNode | None:
    if shape is None:
        return None
    return TreeNode(0, grow(shape[0]), grow(shape[1]))


def shape_depth(shape: Shape) -> int:
    return 0 if shape is None else 1 + max(shape_depth(shape[0]), shape_depth(shape[1]))


def by_definition(shape: Shape) -> bool:
    """Check the condition at this node, then at every node below it."""
    if shape is None:
        return True
    return (
        abs(shape_depth(shape[0]) - shape_depth(shape[1])) <= 1
        and by_definition(shape[0])
        and by_definition(shape[1])
    )


def left_chain(length: int) -> TreeNode | None:
    node = None
    for _ in range(length):
        node = TreeNode(0, node)
    return node


def test_accepts_a_balanced_tree() -> None:
    """Accepts a tree whose subtrees are within one level of each other everywhere."""
    root = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))

    assert is_balanced(root)


def test_accepts_an_empty_tree_and_a_single_node() -> None:
    """Accepts no tree at all and a tree of one node."""
    assert is_balanced(None)
    assert is_balanced(TreeNode(1))


def test_a_difference_of_one_is_allowed() -> None:
    """Accepts a node with one child and a node whose sides differ by one level."""
    assert is_balanced(TreeNode(1, TreeNode(2)))
    assert is_balanced(TreeNode(1, TreeNode(2, TreeNode(3)), TreeNode(4)))


def test_rejects_a_chain() -> None:
    """Rejects a tree whose root has a side two levels deeper than the other."""
    assert not is_balanced(TreeNode(1, TreeNode(2, TreeNode(3))))
    assert not is_balanced(TreeNode(1, None, TreeNode(2, None, TreeNode(3))))


def test_checks_every_node_and_not_just_the_root() -> None:
    """Rejects a tree that is level at the root and lopsided further down.

    Both sides of the root are three deep. Each side is a chain.
    """
    left = TreeNode(2, TreeNode(3, TreeNode(4)))
    right = TreeNode(2, None, TreeNode(3, None, TreeNode(4)))

    assert not is_balanced(TreeNode(1, left, right))


def test_an_imbalance_on_one_side_only_is_still_one() -> None:
    """Rejects a tree with a single unbalanced subtree, on either side."""
    lopsided = TreeNode(2, TreeNode(3, TreeNode(4)))
    level = TreeNode(5, TreeNode(6, TreeNode(8)), TreeNode(7))

    assert not is_balanced(TreeNode(1, lopsided, level))
    assert not is_balanced(
        TreeNode(1, level, TreeNode(2, None, TreeNode(3, None, TreeNode(4))))
    )


def test_balance_is_about_depth_and_not_about_leaves() -> None:
    """Rejects a tree whose leaves are all at the same level but which is lopsided.

    A root with a chain of two on the left and nothing on the right has every
    one of its leaves at depth 3. Its right subtree still has depth 0.
    """
    assert not is_balanced(TreeNode(1, TreeNode(2, TreeNode(3)), None))


def test_balance_is_not_about_the_number_of_nodes() -> None:
    """Accepts a tree with many more nodes on one side when the depths are close."""
    full = TreeNode(
        2, TreeNode(3, TreeNode(5), TreeNode(6)), TreeNode(4, TreeNode(7), TreeNode(8))
    )
    thin = TreeNode(9, TreeNode(10))

    assert is_balanced(TreeNode(1, full, thin))


def test_agrees_with_the_definition_on_every_small_shape() -> None:
    """Matches a node-by-node check for every tree shape of up to nine nodes."""
    balanced = 0
    for size in range(10):
        for shape in shapes(size):
            expected = by_definition(shape)
            assert is_balanced(grow(shape)) == expected, shape
            balanced += expected
    assert 50 < balanced < 1000


def test_leaves_the_tree_alone() -> None:
    """Does not modify the tree."""
    root = TreeNode(1, TreeNode(2), TreeNode(3))

    is_balanced(root)

    assert (root.value, root.left.value, root.right.value) == (1, 2, 3)


def test_handles_a_large_balanced_tree() -> None:
    """Accepts a full tree of four thousand nodes, and rejects it with a tail added."""

    def full(depth: int) -> TreeNode:
        if depth == 1:
            return TreeNode(0)
        return TreeNode(0, full(depth - 1), full(depth - 1))

    tree = full(12)
    assert is_balanced(tree)

    leaf = tree
    while leaf.left is not None:
        leaf = leaf.left
    leaf.left = TreeNode(0, TreeNode(0))
    assert not is_balanced(tree)


def test_handles_a_deep_lopsided_tree() -> None:
    """Rejects a chain of four hundred nodes, and a level root above two of them."""
    assert not is_balanced(left_chain(400))
    assert not is_balanced(TreeNode(0, left_chain(400), left_chain(400)))
