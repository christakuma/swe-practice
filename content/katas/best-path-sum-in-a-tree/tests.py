"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from __future__ import annotations

from itertools import product

from solution import TreeNode, best_path_sum


def build(values: list[int | None]) -> TreeNode | None:
    """Build a tree from a level-order list, with None for a missing child."""
    if not values or values[0] is None:
        return None
    root = TreeNode(int(values[0]))
    queue = [root]
    index = 1
    while queue and index < len(values):
        node = queue.pop(0)
        for side in ("left", "right"):
            if index >= len(values):
                break
            value = values[index]
            index += 1
            if value is not None:
                child = TreeNode(int(value))
                setattr(node, side, child)
                queue.append(child)
    return root


def brute(root: TreeNode) -> int:
    """Max simple-path sum over the tree as an undirected graph -- an oracle.

    It enumerates paths outright and shares nothing with the single-pass
    recursion, in particular nothing with the return-versus-record split.
    """
    nodes: list[TreeNode] = []
    adjacency: dict[int, list[TreeNode]] = {}

    def collect(node: TreeNode, parent: TreeNode | None) -> None:
        nodes.append(node)
        adjacency.setdefault(id(node), [])
        if parent is not None:
            adjacency[id(node)].append(parent)
            adjacency[id(parent)].append(node)
        if node.left is not None:
            collect(node.left, node)
        if node.right is not None:
            collect(node.right, node)

    collect(root, None)
    best = float("-inf")

    def walk(node: TreeNode, seen: frozenset[int], total: int) -> None:
        nonlocal best
        best = max(best, total)
        for other in adjacency[id(node)]:
            if id(other) not in seen:
                walk(other, seen | {id(other)}, total + other.value)

    for node in nodes:
        walk(node, frozenset({id(node)}), node.value)
    return int(best)


def test_turns_at_the_root() -> None:
    """Uses both children and the root when that is best."""
    assert best_path_sum(build([1, 2, 3])) == 6


def test_finds_a_path_that_avoids_the_root() -> None:
    """Finds the best path when the root is worth avoiding.

    The answer is 15 + 20 + 7 and never touches the -10. A solution that only
    considers paths through the root reports 35.
    """
    assert best_path_sum(build([-10, 9, 20, None, None, 15, 7])) == 42


def test_handles_a_single_node() -> None:
    """Returns the only value, even when negative."""
    assert best_path_sum(TreeNode(5)) == 5
    assert best_path_sum(TreeNode(-3)) == -3


def test_handles_an_all_negative_tree() -> None:
    """Returns the least bad single node when every value is negative.

    A path must contain at least one node, so the answer is negative. Seeding
    the running best at 0 instead of negative infinity reports 0 here -- which
    is not the sum of any path.
    """
    assert best_path_sum(build([-3])) == -3
    assert best_path_sum(build([-2, -1, -3])) == -1
    assert best_path_sum(build([-5, -4, -6, -7, -8])) == -4


def test_skips_a_child_that_would_cost() -> None:
    """Leaves out a subtree whose best downward path is negative."""
    assert best_path_sum(build([2, -1, 3])) == 5
    assert best_path_sum(build([2, -1, -1])) == 2


def test_does_not_reuse_a_node() -> None:
    """Counts each node at most once in a path.

    A recursion that returns the *turning* value rather than the best downward
    value lets a parent extend into a subtree that already turned, which visits
    a node twice and inflates the answer.
    """
    assert best_path_sum(build([1, 2, 3, 4, 5, 6, 7])) == 18


def test_handles_a_long_descending_chain() -> None:
    """Sums a path that runs straight down without turning."""
    tree = build([1, 2, None, 3, None, 4])

    assert best_path_sum(tree) == 10


def test_handles_zeros() -> None:
    """Treats zero as a value that may be included or not."""
    assert best_path_sum(build([0])) == 0
    assert best_path_sum(build([0, 0, 0])) == 0
    assert best_path_sum(build([0, -1, 5])) == 5


def test_handles_a_deep_one_sided_tree() -> None:
    """Handles a tree that is effectively a linked list."""
    root = TreeNode(1)
    node = root
    for _ in range(499):
        node.right = TreeNode(1)
        node = node.right

    assert best_path_sum(root) == 500


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a float.

    Seeding with float("-inf") is the natural thing to do and leaks a float
    into the answer unless it is converted back.
    """
    assert type(best_path_sum(TreeNode(1))) is int
    assert type(best_path_sum(build([-1, -2]))) is int


def test_agrees_with_brute_force_on_every_small_layout() -> None:
    """Matches a path-enumerating oracle for every small tree.

    Every level-order layout of four slots over {-2, -1, 3, None}, so every
    arrangement of present and absent children crossed with every mix of
    signs -- a few hundred trees. The zero-floor bug and the
    return-versus-record bug each need particular sign patterns.
    """
    for values in product([-2, -1, 3, None], repeat=4):
        layout = list(values)
        if layout[0] is None:
            continue
        tree = build(layout)
        assert tree is not None

        assert best_path_sum(tree) == brute(tree), layout


def test_agrees_with_brute_force_on_larger_layouts() -> None:
    """Matches the oracle for every level-order layout of six slots.

    Deeper trees, so a path can turn below the root and still not be the whole
    subtree -- the case a shallow sweep cannot produce.
    """
    for values in product([-2, 1, None], repeat=6):
        layout = list(values)
        if layout[0] is None:
            continue
        tree = build(layout)
        assert tree is not None

        assert best_path_sum(tree) == brute(tree), layout
