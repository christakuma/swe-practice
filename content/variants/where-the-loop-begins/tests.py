"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc

from solution import ListNode, cycle_start


def build(length: int, entry: int | None = None) -> list[ListNode]:
    """`length` nodes in a line, the last pointing at node `entry` if given."""
    nodes = [ListNode(value) for value in range(length)]
    for index in range(length - 1):
        nodes[index].next_node = nodes[index + 1]
    if entry is not None:
        nodes[-1].next_node = nodes[entry]
    return nodes


def test_finds_a_cycle_that_begins_part_way_along() -> None:
    """Returns the node the tail points back at."""
    nodes = build(5, entry=2)

    assert cycle_start(nodes[0]) is nodes[2]


def test_finds_a_cycle_that_begins_at_the_head() -> None:
    """Returns the head when the whole list is one loop."""
    nodes = build(4, entry=0)

    assert cycle_start(nodes[0]) is nodes[0]


def test_finds_a_node_that_points_at_itself() -> None:
    """Returns a node that is its own successor."""
    alone = build(1, entry=0)
    tail = build(6, entry=5)

    assert cycle_start(alone[0]) is alone[0]
    assert cycle_start(tail[0]) is tail[5]


def test_returns_none_for_a_list_that_ends() -> None:
    """Returns None when the list reaches its end."""
    assert cycle_start(build(1)[0]) is None
    assert cycle_start(build(2)[0]) is None
    assert cycle_start(build(7)[0]) is None


def test_returns_none_for_no_list_at_all() -> None:
    """Returns None for an empty list."""
    assert cycle_start(None) is None


def test_returns_the_node_and_not_its_value() -> None:
    """Returns the node object, among several nodes holding the same value."""
    nodes = build(5, entry=3)
    for node in nodes:
        node.value = 7

    assert cycle_start(nodes[0]) is nodes[3]


def test_finds_the_start_for_every_length_and_every_entry_point() -> None:
    """Finds the start for every list up to twelve nodes and every entry point."""
    for length in range(1, 13):
        for entry in range(length):
            nodes = build(length, entry)
            assert cycle_start(nodes[0]) is nodes[entry], (length, entry)


def test_leaves_the_list_as_it_found_it() -> None:
    """Changes no node's successor and no node's value."""
    nodes = build(8, entry=3)
    before = [(node.value, node.next_node) for node in nodes]

    cycle_start(nodes[0])

    assert [(node.value, node.next_node) for node in nodes] == before


def test_walks_a_long_list_that_ends() -> None:
    """Walks a hundred thousand nodes without recursing."""
    assert cycle_start(build(100_000)[0]) is None


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the list.

    A hundred thousand nodes with the cycle closing ten from the end. A set
    of the nodes already seen holds almost all of them before it finds the
    repeat, which is megabytes; two pointers are two references. The list is
    built before measuring starts.
    """
    nodes = build(100_000, entry=99_990)

    tracemalloc.start()
    found = cycle_start(nodes[0])
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert found is nodes[99_990]
    assert peak < 64_000, f"allocated {peak} bytes"
