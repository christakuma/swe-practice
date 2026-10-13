"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import re
from collections.abc import Iterator

from solution import TreeNode, deserialize, serialize

type Shape = tuple["Shape", "Shape"] | None

ONLY_NUMBERS = re.compile(r"-?\d+(,-?\d+)*")


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


def search_tree(shape: Shape, low: int = 0, step: int = 1) -> TreeNode | None:
    """The search tree of this shape holding low, low + step, low + 2 * step, ..."""
    if shape is None:
        return None
    value = low + step * size_of(shape[0])
    return TreeNode(
        value,
        search_tree(shape[0], low, step),
        search_tree(shape[1], value + step, step),
    )


def layout(root: TreeNode | None) -> dict[str, int]:
    """Each node's value keyed by its path from the root."""
    found: dict[str, int] = {}
    pending = [(root, "")]
    while pending:
        node, path = pending.pop()
        if node is not None:
            found[path] = node.value
            pending.append((node.left, path + "L"))
            pending.append((node.right, path + "R"))
    return found


def round_trip(root: TreeNode | None) -> TreeNode | None:
    """Serialise, check the string is values and nothing else, and rebuild."""
    data = serialize(root)
    count = len(layout(root))
    assert isinstance(data, str)
    if count == 0:
        assert data == ""
    else:
        assert ONLY_NUMBERS.fullmatch(data), (
            f"not only numbers and commas: {data[:60]!r}"
        )
        assert len(data.split(",")) == count, "not exactly one number per node"
    return deserialize(data)


def test_round_trips_a_small_tree() -> None:
    """Rebuilds a three-node tree."""
    root = TreeNode(2, TreeNode(1), TreeNode(3))

    assert layout(round_trip(root)) == {"": 2, "L": 1, "R": 3}


def test_an_empty_tree_is_the_empty_string() -> None:
    """Serialises no tree to "" and "" back to no tree."""
    assert serialize(None) == ""
    assert deserialize("") is None


def test_writes_one_number_per_node_and_nothing_else() -> None:
    """Uses only integers and commas, with no marker for a missing child."""
    root = TreeNode(5, TreeNode(3, None, TreeNode(4)), TreeNode(8))

    data = serialize(root)

    assert ONLY_NUMBERS.fullmatch(data)
    assert sorted(int(part) for part in data.split(",")) == [3, 4, 5, 8]


def test_keeps_a_lone_child_on_its_own_side() -> None:
    """Tells a single left child from a single right child."""
    left = TreeNode(5, TreeNode(3))
    right = TreeNode(5, None, TreeNode(8))

    assert layout(round_trip(left)) == {"": 5, "L": 3}
    assert layout(round_trip(right)) == {"": 5, "R": 8}


def test_keeps_shape_and_not_just_the_values() -> None:
    """Rebuilds each of several different trees holding the same values.

    The values 1 to 3 make five different search trees. All five have the
    same values in ascending order, so an encoding that sorts cannot tell
    them apart.
    """
    seen = set()
    for shape in shapes(3):
        tree = search_tree(shape, low=1)
        assert layout(round_trip(tree)) == layout(tree)
        seen.add(serialize(tree))
    assert len(seen) == 5


def test_handles_chains() -> None:
    """Rebuilds trees that lean entirely one way."""
    rising = TreeNode(1, None, TreeNode(2, None, TreeNode(3)))
    falling = TreeNode(3, TreeNode(2, TreeNode(1)))

    assert layout(round_trip(rising)) == {"": 1, "R": 2, "RR": 3}
    assert layout(round_trip(falling)) == {"": 3, "L": 2, "LL": 1}


def test_handles_negative_and_large_values() -> None:
    """Keeps minus signs and many-digit values intact."""
    root = TreeNode(0, TreeNode(-(10**9), None, TreeNode(-7)), TreeNode(10**9))

    assert layout(round_trip(root)) == {"": 0, "L": -(10**9), "LR": -7, "R": 10**9}


def test_a_single_node() -> None:
    """Rebuilds a tree of one node, including one holding zero or a negative."""
    for value in (0, 7, -3):
        assert layout(round_trip(TreeNode(value))) == {"": value}
        assert serialize(TreeNode(value)) == str(value)


def test_round_trips_every_small_search_tree() -> None:
    """Rebuilds every search tree shape of up to eight nodes exactly."""
    for size in range(9):
        for shape in shapes(size):
            tree = search_tree(shape, low=-6, step=3)
            assert layout(round_trip(tree)) == layout(tree), shape


def test_returns_a_new_tree_and_leaves_the_original_alone() -> None:
    """Builds fresh nodes and does not modify the tree it serialised."""
    root = TreeNode(2, TreeNode(1), TreeNode(3))

    copy = round_trip(root)

    assert copy is not root
    assert layout(root) == {"": 2, "L": 1, "R": 3}


def test_round_trips_a_large_tree() -> None:
    """Rebuilds a balanced tree of a hundred thousand nodes."""

    def balanced(low: int, high: int) -> TreeNode | None:
        if low >= high:
            return None
        middle = (low + high) // 2
        return TreeNode(middle, balanced(low, middle), balanced(middle + 1, high))

    tree = balanced(0, 100_000)
    copy = round_trip(tree)

    assert layout(copy) == layout(tree)


def test_round_trips_a_deep_lopsided_tree() -> None:
    """Rebuilds a zigzag five hundred levels deep with a bushy end."""
    root = TreeNode(0)
    node, low, high = root, 0, 10_000
    for depth in range(1, 500):
        if depth % 2:
            high -= 1
            node.right = TreeNode(high)
            node = node.right
        else:
            low += 1
            node.left = TreeNode(low)
            node = node.left

    assert layout(round_trip(root)) == layout(root)
