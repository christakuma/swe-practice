"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc
from itertools import pairwise, product

from solution import ListNode, is_palindrome


def build(values: list[int]) -> tuple[ListNode | None, list[ListNode]]:
    """A list holding `values`, and its nodes in order."""
    nodes = [ListNode(value) for value in values]
    for node, following in pairwise(nodes):
        node.next_node = following
    return (nodes[0] if nodes else None), nodes


def intact(nodes: list[ListNode], values: list[int]) -> bool:
    """Whether every node still holds its value and points at the next one."""
    followers = [*nodes[1:], None] if nodes else []
    return all(
        node.value == value and node.next_node is following
        for node, value, following in zip(nodes, values, followers, strict=True)
    )


def test_accepts_an_even_palindrome() -> None:
    """Accepts a list whose two halves mirror each other."""
    assert is_palindrome(build([1, 2, 2, 1])[0])
    assert is_palindrome(build([7, 7])[0])


def test_accepts_an_odd_palindrome() -> None:
    """Accepts a list with a middle node that has no partner."""
    assert is_palindrome(build([1, 2, 3, 2, 1])[0])
    assert is_palindrome(build([4, 9, 4])[0])


def test_rejects_a_list_that_is_not_one() -> None:
    """Rejects lists that read differently backwards."""
    assert not is_palindrome(build([1, 2, 3])[0])
    assert not is_palindrome(build([1, 2])[0])
    assert not is_palindrome(build([1, 2, 3, 1])[0])


def test_rejects_a_difference_at_the_very_ends() -> None:
    """Rejects a list whose first and last values differ and nothing else does."""
    assert not is_palindrome(build([1, 5, 5, 2])[0])
    assert not is_palindrome(build([1, 5, 6, 5, 2])[0])


def test_rejects_a_difference_next_to_the_middle() -> None:
    """Rejects a list whose only mismatch is the pair around the centre."""
    assert not is_palindrome(build([1, 2, 3, 1])[0])
    assert not is_palindrome(build([1, 2, 9, 3, 1])[0])


def test_an_empty_list_and_a_single_node_are_palindromes() -> None:
    """Accepts no list at all and a list of one node."""
    assert is_palindrome(None)
    assert is_palindrome(build([5])[0])


def test_compares_values_exactly() -> None:
    """Does not treat a value and its negative, or zero and nothing, as equal."""
    assert not is_palindrome(build([3, -3])[0])
    assert is_palindrome(build([0, 0, 0])[0])
    assert not is_palindrome(build([0, 1, 1])[0])


def test_agrees_with_reversing_a_python_list() -> None:
    """Matches a list-reversal check for every short list.

    Every list of up to seven values drawn from 0, 1, 2.
    """
    for size in range(8):
        for chosen in product(range(3), repeat=size):
            values = list(chosen)
            head, nodes = build(values)
            assert is_palindrome(head) == (values == values[::-1]), values
            assert intact(nodes, values), values


def test_leaves_a_palindrome_as_it_found_it() -> None:
    """Restores every link after answering True."""
    for values in ([1, 2, 2, 1], [1, 2, 3, 2, 1], [8], [8, 8]):
        head, nodes = build(values)

        assert is_palindrome(head)
        assert intact(nodes, values), values


def test_leaves_a_non_palindrome_as_it_found_it() -> None:
    """Restores every link after answering False, wherever the mismatch was."""
    for values in ([1, 2, 3, 4], [1, 2, 3, 4, 5], [1, 2, 2, 9], [9, 2, 3, 2, 1]):
        head, nodes = build(values)

        assert not is_palindrome(head)
        assert intact(nodes, values), values


def test_can_be_asked_twice() -> None:
    """Gives the same answer when asked about the same list again."""
    head, _ = build([1, 2, 3, 2, 1])

    assert is_palindrome(head)
    assert is_palindrome(head)


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the list.

    A palindrome of a hundred thousand nodes. Copying the values out takes a
    list of a hundred thousand references; reversing half of the nodes in
    place takes none. The list is built before measuring starts.
    """
    half = list(range(50_000))
    head, nodes = build(half + half[::-1])

    tracemalloc.start()
    answer = is_palindrome(head)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert answer
    assert peak < 64_000, f"allocated {peak} bytes"
    assert nodes[49_999].next_node is nodes[50_000]
    assert nodes[-1].next_node is None


def test_reads_a_long_list_that_is_not_a_palindrome() -> None:
    """Rejects a hundred thousand nodes that differ only at the two ends."""
    values = [1, *([4] * 99_998), 2]
    head, nodes = build(values)

    assert not is_palindrome(head)
    assert intact(nodes, values)
