"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc

from solution import ListNode, cycle_length


def build(length: int, entry: int | None = None) -> list[ListNode]:
    """`length` nodes in a line, the last pointing at node `entry` if given."""
    nodes = [ListNode(value) for value in range(length)]
    for index in range(length - 1):
        nodes[index].next_node = nodes[index + 1]
    if entry is not None:
        nodes[-1].next_node = nodes[entry]
    return nodes


def test_measures_a_cycle_with_a_lead_in() -> None:
    """Counts only the nodes that go round, not the ones leading to them."""
    assert cycle_length(build(5, entry=2)[0]) == 3
    assert cycle_length(build(10, entry=7)[0]) == 3


def test_measures_a_list_that_is_all_cycle() -> None:
    """Counts every node when the last one points back at the head."""
    assert cycle_length(build(4, entry=0)[0]) == 4
    assert cycle_length(build(2, entry=0)[0]) == 2


def test_a_node_pointing_at_itself_is_a_cycle_of_one() -> None:
    """Returns 1 for a self-loop, alone or at the end of a list."""
    assert cycle_length(build(1, entry=0)[0]) == 1
    assert cycle_length(build(6, entry=5)[0]) == 1


def test_returns_zero_for_a_list_that_ends() -> None:
    """Returns 0 when the list reaches its end."""
    assert cycle_length(build(1)[0]) == 0
    assert cycle_length(build(2)[0]) == 0
    assert cycle_length(build(7)[0]) == 0


def test_returns_zero_for_no_list_at_all() -> None:
    """Returns 0 for an empty list."""
    assert cycle_length(None) == 0


def test_a_long_lead_in_does_not_inflate_the_answer() -> None:
    """Returns the cycle's length when the lead-in is many times longer.

    Nine nodes lead to a cycle of two. The two pointers go round several
    times before they meet, so the number of steps they took is not 2.
    """
    assert cycle_length(build(11, entry=9)[0]) == 2
    assert cycle_length(build(40, entry=37)[0]) == 3


def test_does_not_rely_on_values() -> None:
    """Measures a cycle in a list whose nodes all hold the same value."""
    nodes = build(9, entry=4)
    for node in nodes:
        node.value = 7

    assert cycle_length(nodes[0]) == 5


def test_measures_every_cycle_in_every_short_list() -> None:
    """Measures the cycle for every list up to fourteen nodes and every entry point."""
    for length in range(1, 15):
        for entry in range(length):
            nodes = build(length, entry)
            assert cycle_length(nodes[0]) == length - entry, (length, entry)


def test_leaves_the_list_as_it_found_it() -> None:
    """Changes no node's successor and no node's value."""
    nodes = build(8, entry=3)
    before = [(node.value, node.next_node) for node in nodes]

    cycle_length(nodes[0])

    assert [(node.value, node.next_node) for node in nodes] == before


def test_walks_a_long_list_that_ends() -> None:
    """Walks a hundred thousand nodes without recursing."""
    assert cycle_length(build(100_000)[0]) == 0


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the list.

    A hundred thousand nodes, the last pointing back at the thousandth. A set
    of the nodes already seen holds every one of them before it finds the
    repeat. The list is built before measuring starts.
    """
    nodes = build(100_000, entry=1_000)

    tracemalloc.start()
    length = cycle_length(nodes[0])
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert length == 99_000
    assert peak < 64_000, f"allocated {peak} bytes"
