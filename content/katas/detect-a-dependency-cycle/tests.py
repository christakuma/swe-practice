"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import has_cycle


def test_finds_a_two_node_cycle() -> None:
    """Finds the shortest possible cycle between two nodes."""
    assert has_cycle({"a": ["b"], "b": ["a"]}) is True


def test_finds_a_longer_cycle() -> None:
    """Finds a cycle that goes round three nodes."""
    assert has_cycle({"a": ["b"], "b": ["c"], "c": ["a"]}) is True


def test_finds_a_self_dependency() -> None:
    """Treats a node depending on itself as a cycle."""
    assert has_cycle({"a": ["a"]}) is True


def test_accepts_a_chain() -> None:
    """Reports no cycle for a straight chain of dependencies."""
    assert has_cycle({"a": ["b"], "b": ["c"], "c": []}) is False


def test_accepts_a_diamond() -> None:
    """Reports no cycle when two paths rejoin at the same node.

    The case that rules out a single visited set. `d` is reached from both `b`
    and `c`, so it is visited twice -- legitimately. A solution that calls any
    revisit a cycle says True here.
    """
    assert has_cycle({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}) is False


def test_accepts_an_empty_graph() -> None:
    """Reports no cycle for no dependencies."""
    assert has_cycle({}) is False


def test_accepts_independent_nodes() -> None:
    """Reports no cycle when nothing depends on anything."""
    assert has_cycle({"a": [], "b": [], "c": []}) is False


def test_finds_a_cycle_in_a_second_component() -> None:
    """Finds a cycle that is not reachable from the first node examined.

    A solution that starts from one node and stops misses this entirely.
    """
    graph = {"a": ["b"], "b": [], "x": ["y"], "y": ["x"]}

    assert has_cycle(graph) is True


def test_handles_a_dependency_with_no_entry_of_its_own() -> None:
    """Handles a name that appears as a dependency and never as a key.

    `b` has no entry, which is how a leaf is usually represented. A solution
    indexing the dict directly raises KeyError.
    """
    assert has_cycle({"a": ["b"]}) is False


def test_handles_a_deep_chain_quickly() -> None:
    """Walks a chain far deeper than Python will recurse.

    Ten thousand dependencies in a line. A recursive walk raises
    RecursionError; an explicit stack does not.
    """
    length = 10_000
    graph = {f"n{index}": [f"n{index + 1}"] for index in range(length)}
    graph[f"n{length}"] = []

    assert has_cycle(graph) is False


def test_finds_a_cycle_at_the_end_of_a_deep_chain() -> None:
    """Finds a cycle buried at the bottom of a long chain."""
    length = 5_000
    graph: dict[str, list[str]] = {
        f"n{index}": [f"n{index + 1}"] for index in range(length)
    }
    graph[f"n{length}"] = ["n0"]

    assert has_cycle(graph) is True
