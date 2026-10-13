"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import Node, copy_list


def build(values: list[int], targets: tuple[int | None, ...]) -> list[Node]:
    """Nodes in a line; node i's random pointer goes to node targets[i]."""
    nodes = [Node(value) for value in values]
    for index, node in enumerate(nodes):
        if index + 1 < len(nodes):
            node.next = nodes[index + 1]
        target = targets[index]
        node.random = None if target is None else nodes[target]
    return nodes


def walk(head: Node | None) -> list[Node]:
    found = []
    while head is not None:
        assert len(found) < 100_000, "the list does not end"
        found.append(head)
        head = head.next
    return found


def pattern(nodes: list[Node]) -> list[tuple[int, int | None]]:
    """Each node's value and the position its random pointer leads to."""
    where = {id(node): index for index, node in enumerate(nodes)}
    return [
        (node.value, None if node.random is None else where[id(node.random)])
        for node in nodes
    ]


def test_copies_values_and_both_pointers() -> None:
    """Reproduces the values, the order and every random pointer."""
    originals = build([7, 13, 11, 10, 1], (None, 0, 4, 2, 0))

    copies = walk(copy_list(originals[0]))

    assert pattern(copies) == [(7, None), (13, 0), (11, 4), (10, 2), (1, 0)]


def test_shares_no_node_with_the_original() -> None:
    """Creates every node of the copy afresh, including random targets."""
    originals = build([1, 2, 3], (2, 0, 1))

    copies = walk(copy_list(originals[0]))

    assert not {id(node) for node in originals} & {id(node) for node in copies}
    assert all(node.random in copies for node in copies)


def test_copies_a_node_that_points_at_itself() -> None:
    """Makes a self-pointing node's copy point at the copy."""
    originals = build([5], (0,))

    copy = copy_list(originals[0])

    assert copy is not None
    assert copy.random is copy
    assert copy is not originals[0]


def test_handles_an_empty_list_and_no_random_pointers() -> None:
    """Returns None for None, and copies missing pointers as missing."""
    assert copy_list(None) is None
    copy = copy_list(build([5], (None,))[0])
    assert copy is not None
    assert (copy.random, copy.next) == (None, None)


def test_leaves_the_original_untouched() -> None:
    """Changes no pointer and no value in the original list."""
    originals = build([1, 2, 3], (1, 2, 0))
    before = [(node.value, node.next, node.random) for node in originals]

    copy_list(originals[0])

    assert [(node.value, node.next, node.random) for node in originals] == before


def test_tells_nodes_apart_by_identity() -> None:
    """Copies the pointer pattern correctly when every value is the same."""
    originals = build([4, 4, 4], (2, None, 1))

    assert pattern(walk(copy_list(originals[0]))) == [(4, 2), (4, None), (4, 1)]


def test_copies_every_pattern_of_pointers_on_short_lists() -> None:
    """Reproduces every possible pattern of random pointers up to four nodes."""
    for length in range(1, 5):
        for targets in product([None, *range(length)], repeat=length):
            originals = build(list(range(length)), targets)
            copies = walk(copy_list(originals[0]))
            assert pattern(copies) == pattern(originals), targets
            assert not {id(node) for node in originals} & {id(node) for node in copies}


def test_copies_a_long_list() -> None:
    """Copies ten thousand nodes without recursing."""
    size = 10_000
    targets = tuple((index * 7) % size for index in range(size))
    originals = build(list(range(size)), targets)

    assert pattern(walk(copy_list(originals[0]))) == pattern(originals)
