"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import Node, deserialize, serialize


def print_of(node: Node | None) -> tuple | None:
    """A small tree as nested tuples, child order included."""
    if node is None:
        return None
    return (node.value, tuple(print_of(child) for child in node.children))


def forests(count: int) -> list[list[tuple]]:
    """Every ordered forest with `count` nodes, as shapes without values."""
    if count == 0:
        return [[]]
    found = []
    for first in range(1, count + 1):
        for children in forests(first - 1):
            for rest in forests(count - first):
                found.append([tuple(children), *rest])
    return found


def grown(shape: tuple, counter: list[int]) -> Node:
    """A tree of the given shape, numbered in pre-order."""
    node = Node(counter[0])
    counter[0] += 1
    node.children = [grown(child, counter) for child in shape]
    return node


def test_recovers_a_small_tree() -> None:
    """Recovers values, shape and child order."""
    root = Node(1, [Node(3, [Node(5), Node(6)]), Node(2), Node(4)])

    assert print_of(deserialize(serialize(root))) == print_of(root)


def test_recovers_an_empty_tree_and_a_single_node() -> None:
    """Recovers None as None and one node as one node."""
    assert deserialize(serialize(None)) is None
    assert print_of(deserialize(serialize(Node(7)))) == (7, ())


def test_keeps_the_order_of_children() -> None:
    """Does not sort or reverse a node's children."""
    root = Node(0, [Node(3), Node(1), Node(2)])

    assert print_of(deserialize(serialize(root))) == (0, ((3, ()), (1, ()), (2, ())))


def test_recovers_negative_and_repeated_values() -> None:
    """Recovers negative, multi-digit and repeated values."""
    root = Node(-12, [Node(-12), Node(0, [Node(1000000000)])])

    assert print_of(deserialize(serialize(root))) == print_of(root)


def test_distinguishes_shapes_with_the_same_pre_order() -> None:
    """Gives different strings to different trees with the same values in order."""
    chain = Node(1, [Node(2, [Node(3)])])
    fan = Node(1, [Node(2), Node(3)])

    assert serialize(chain) != serialize(fan)


def test_returns_the_declared_types() -> None:
    """Returns a str from serialize and a Node or None from deserialize."""
    assert isinstance(serialize(Node(1)), str)
    assert isinstance(serialize(None), str)
    assert isinstance(deserialize(serialize(Node(1))), Node)


def test_round_trips_every_small_shape_and_keeps_them_apart() -> None:
    """Recovers every tree of up to seven nodes, each from a distinct string."""
    for size in range(1, 8):
        seen = set()
        for children in forests(size - 1):
            root = grown(tuple(children), [0])
            packed = serialize(root)
            assert print_of(deserialize(packed)) == print_of(root)
            seen.add(packed)
        assert len(seen) == len(forests(size - 1)), size


def test_handles_a_very_deep_and_a_very_wide_tree() -> None:
    """Round trips a chain ten thousand deep and a node with 50,000 children."""
    root = Node(0)
    node = root
    for value in range(1, 10_000):
        child = Node(value)
        node.children.append(child)
        node = child

    copy = deserialize(serialize(root))
    depth = 0
    while copy is not None:
        assert copy.value == depth
        copy = copy.children[0] if copy.children else None
        depth += 1
    assert depth == 10_000

    wide = Node(-1, [Node(value) for value in range(50_000)])
    back = deserialize(serialize(wide))
    assert back is not None
    assert [child.value for child in back.children] == list(range(50_000))
