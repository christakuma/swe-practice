"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from __future__ import annotations

from solution import TreeNode, invert


def build(values: list[int | None]) -> TreeNode | None:
    """Build a tree from a level-order list, with None for a missing child."""
    if not values or values[0] is None:
        return None
    root = TreeNode(int(values[0]))
    queue = [root]
    index = 1
    while queue and index < len(values):
        node = queue.pop(0)
        if index < len(values):
            value = values[index]
            index += 1
            if value is not None:
                node.left = TreeNode(int(value))
                queue.append(node.left)
        if index < len(values):
            value = values[index]
            index += 1
            if value is not None:
                node.right = TreeNode(int(value))
                queue.append(node.right)
    return root


def levels(root: TreeNode | None) -> list[list[int | None]]:
    """Read the tree level by level, recording None for missing children."""
    if root is None:
        return []
    out: list[list[int | None]] = []
    current: list[TreeNode | None] = [root]
    while any(node is not None for node in current):
        out.append([node.value if node else None for node in current])
        nxt: list[TreeNode | None] = []
        for node in current:
            nxt.append(node.left if node else None)
            nxt.append(node.right if node else None)
        current = nxt
    return out


def test_inverts_a_full_tree() -> None:
    """Mirrors every level of a complete tree."""
    tree = build([4, 2, 7, 1, 3, 6, 9])

    assert levels(invert(tree)) == [[4], [7, 2], [9, 6, 3, 1]]


def test_handles_an_empty_tree() -> None:
    """Returns None for an empty tree."""
    assert invert(None) is None


def test_handles_a_single_node() -> None:
    """Returns a one-node tree unchanged."""
    tree = TreeNode(1)

    assert invert(tree) is tree
    assert levels(tree) == [[1]]


def test_inverts_a_lopsided_tree() -> None:
    """Moves a single child to the other side.

    A left-only chain must become a right-only chain. A solution that swaps
    only when both children exist leaves this untouched.

    `levels` pads each row to the full width for its depth, so absent nodes
    read as None and a mirrored position is visible rather than collapsed.
    """
    tree = build([1, 2, None, 3])

    assert levels(tree) == [[1], [2, None], [3, None, None, None]]
    assert levels(invert(tree)) == [[1], [None, 2], [None, None, None, 3]]


def test_inverts_recursively_not_just_at_the_root() -> None:
    """Swaps children at every depth, not only at the root.

    Swapping the root's two subtrees without descending gives
    [[1], [3, 2], [6, 7, 4, 5]] -- the top level is right and the bottom is
    not.
    """
    tree = build([1, 2, 3, 4, 5, 6, 7])

    assert levels(invert(tree)) == [[1], [3, 2], [7, 6, 5, 4]]


def test_returns_the_node_the_caller_holds() -> None:
    """Returns the original root rather than a rebuilt tree.

    The caller keeps its reference, so a solution that builds a mirrored copy
    appears to do nothing from the outside.
    """
    tree = build([4, 2, 7])
    original_root = tree
    original_left = tree.left

    result = invert(tree)

    assert result is original_root
    assert result.right is original_left


def test_reuses_the_nodes_it_was_given() -> None:
    """Relinks the original nodes rather than copying values between them."""
    tree = build([1, 2, 3])
    left, right = tree.left, tree.right

    invert(tree)

    assert tree.left is right
    assert tree.right is left
    assert left.value == 2
    assert right.value == 3


def test_inverting_twice_returns_the_original() -> None:
    """Restores the tree after two inversions.

    Mirroring is an involution, so this holds for any tree and needs no
    expected-value table -- it catches an inversion that is self-consistent
    but is not a mirror.
    """
    tree = build([5, 3, 8, 1, 4, 7, 9])
    before = levels(tree)

    invert(invert(tree))

    assert levels(tree) == before


def test_inverts_a_deep_tree() -> None:
    """Inverts a tree deep enough to matter without exhausting the stack.

    Five hundred levels of left children become five hundred of right
    children.
    """
    root = TreeNode(0)
    node = root
    for value in range(1, 500):
        node.left = TreeNode(value)
        node = node.left

    invert(root)

    node = root
    depth = 0
    while node.right is not None:
        assert node.left is None
        node = node.right
        depth += 1
    assert depth == 499
