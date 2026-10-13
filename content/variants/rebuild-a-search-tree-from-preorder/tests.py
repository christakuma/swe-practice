"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator

from solution import TreeNode, rebuild

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


def size_of(shape: Shape) -> int:
    return 0 if shape is None else 1 + size_of(shape[0]) + size_of(shape[1])


def expected_layout(shape: Shape, low: int = 0, path: str = "") -> dict[str, int]:
    """Path -> value for the search tree of this shape holding low, low + 1, ..."""
    if shape is None:
        return {}
    value = low + size_of(shape[0])
    return {
        path: value,
        **expected_layout(shape[0], low, path + "L"),
        **expected_layout(shape[1], value + 1, path + "R"),
    }


def preorder_of(layout: dict[str, int]) -> list[int]:
    """Pre-order is the paths in sorted order, with "L" before "R"."""
    return [layout[path] for path in sorted(layout)]


def layout(root: TreeNode | None) -> dict[str, int]:
    """Each node's value keyed by its path from the root, without recursing."""
    found: dict[str, int] = {}
    pending = [(root, "")]
    while pending:
        node, path = pending.pop()
        if node is not None:
            assert isinstance(node, TreeNode)
            found[path] = node.value
            pending.append((node.left, path + "L"))
            pending.append((node.right, path + "R"))
    return found


def test_rebuilds_a_tree_with_both_kinds_of_child() -> None:
    """Places smaller values to the left and larger ones to the right."""
    root = rebuild([8, 5, 1, 7, 10, 12])

    assert layout(root) == {"": 8, "L": 5, "LL": 1, "LR": 7, "R": 10, "RR": 12}


def test_an_empty_list_is_an_empty_tree() -> None:
    """Returns None for no values."""
    assert rebuild([]) is None


def test_a_single_value_is_a_single_node() -> None:
    """Returns a lone node with no children."""
    assert layout(rebuild([4])) == {"": 4}


def test_ascending_values_lean_right() -> None:
    """Builds a right-leaning chain from increasing values."""
    assert layout(rebuild([1, 2, 3])) == {"": 1, "R": 2, "RR": 3}


def test_descending_values_lean_left() -> None:
    """Builds a left-leaning chain from decreasing values."""
    assert layout(rebuild([3, 2, 1])) == {"": 3, "L": 2, "LL": 1}


def test_a_larger_value_climbs_to_the_right_ancestor() -> None:
    """Attaches a value as the right child of the deepest node it exceeds.

    After 5, 3, 1 the value 4 is larger than the 1 and the 3 and smaller than
    the 5: it is the 3's right child, not the 1's and not the 5's.
    """
    assert layout(rebuild([5, 3, 1, 4])) == {"": 5, "L": 3, "LL": 1, "LR": 4}
    assert layout(rebuild([5, 3, 1, 4, 9, 7])) == {
        "": 5,
        "L": 3,
        "LL": 1,
        "LR": 4,
        "R": 9,
        "RL": 7,
    }


def test_a_right_child_can_have_a_left_child() -> None:
    """Goes left again below a node that was reached by going right."""
    assert layout(rebuild([2, 1, 6, 4, 3, 5])) == {
        "": 2,
        "L": 1,
        "R": 6,
        "RL": 4,
        "RLL": 3,
        "RLR": 5,
    }


def test_handles_negative_values() -> None:
    """Orders values below zero correctly."""
    assert layout(rebuild([0, -5, -9, -2, 3])) == {
        "": 0,
        "L": -5,
        "LL": -9,
        "LR": -2,
        "R": 3,
    }


def test_rebuilds_every_small_search_tree() -> None:
    """Rebuilds every search tree shape of up to eight nodes from its pre-order."""
    for size in range(9):
        for shape in shapes(size):
            wanted = expected_layout(shape)
            assert layout(rebuild(preorder_of(wanted))) == wanted, shape


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    preorder = [4, 2, 6]

    rebuild(preorder)

    assert preorder == [4, 2, 6]


def test_builds_a_very_deep_tree_without_recursing() -> None:
    """Builds chains and a zigzag of 100,000 nodes.

    The zigzag is 0, 199999, 1, 199998, ...: each value is the child of the
    one before it, alternating right and left.
    """
    size = 100_000
    node, depth = rebuild(list(range(size))), 0
    while node is not None:
        assert node.value == depth
        assert node.left is None
        node, depth = node.right, depth + 1
    assert depth == size

    zigzag = [
        index // 2 if index % 2 == 0 else 2 * size - 1 - index // 2
        for index in range(size)
    ]
    root = rebuild(zigzag)
    node, depth = root, 0
    while node is not None:
        assert node.value == zigzag[depth]
        node = node.right if depth % 2 == 0 else node.left
        depth += 1
    assert depth == size


def test_builds_a_large_bushy_tree() -> None:
    """Rebuilds a balanced tree of a hundred thousand nodes from its pre-order."""

    def preorder(low: int, high: int) -> list[int]:
        order, pending = [], [(low, high)]
        while pending:
            a, b = pending.pop()
            if a < b:
                middle = (a + b) // 2
                order.append(middle)
                pending.append((middle + 1, b))
                pending.append((a, middle))
        return order

    values = preorder(0, 100_000)
    root = rebuild(values)

    assert root is not None
    assert root.value == 50_000
    found = layout(root)
    assert len(found) == 100_000
    assert [found[path] for path in sorted(found)] == values
