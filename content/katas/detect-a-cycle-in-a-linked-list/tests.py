"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import ListNode, has_cycle


def chain(length: int) -> list[ListNode]:
    """A list of `length` nodes, linked in order, ending at None."""
    nodes = [ListNode(value) for value in range(length)]
    for index in range(length - 1):
        nodes[index].next_node = nodes[index + 1]
    return nodes


def test_finds_a_loop_back_to_the_start() -> None:
    """Finds a list whose last node points at the first."""
    nodes = chain(4)
    nodes[-1].next_node = nodes[0]

    assert has_cycle(nodes[0]) is True


def test_finds_a_loop_back_to_the_middle() -> None:
    """Finds a loop that starts part-way along the list.

    The tail enters the loop rather than being in it, which is the shape that
    breaks a solution comparing the two pointers' *values* instead of their
    identities.
    """
    nodes = chain(6)
    nodes[-1].next_node = nodes[2]

    assert has_cycle(nodes[0]) is True


def test_finds_a_single_node_pointing_at_itself() -> None:
    """Finds the smallest possible loop."""
    node = ListNode(1)
    node.next_node = node

    assert has_cycle(node) is True


def test_accepts_a_list_of_odd_length() -> None:
    """Returns False for an acyclic list with an odd number of nodes.

    The fast pointer lands exactly on the last node here, so the loop condition
    has to check `fast` itself and not only `fast.next_node`.
    """
    assert has_cycle(chain(5)[0]) is False


def test_accepts_a_list_of_even_length() -> None:
    """Returns False for an acyclic list with an even number of nodes.

    The fast pointer lands one short of the end, so the condition has to check
    `fast.next_node` as well.
    """
    assert has_cycle(chain(6)[0]) is False


def test_accepts_a_single_node() -> None:
    """Returns False for one node pointing at nothing."""
    assert has_cycle(ListNode(1)) is False


def test_accepts_an_empty_list() -> None:
    """Returns False for no list at all."""
    assert has_cycle(None) is False


def test_accepts_two_nodes() -> None:
    """Returns False for two nodes in a line."""
    assert has_cycle(chain(2)[0]) is False


def test_finds_a_loop_of_two_at_the_end_of_a_long_tail() -> None:
    """Finds a small loop reached after a long acyclic run."""
    nodes = chain(50)
    nodes[-1].next_node = nodes[-2]

    assert has_cycle(nodes[0]) is True


def test_handles_a_long_list_quickly() -> None:
    """Walks a list far longer than Python will recurse.

    A hundred thousand nodes with no cycle. A recursive walk raises
    RecursionError; two pointers do not recurse at all.
    """
    assert has_cycle(chain(100_000)[0]) is False
