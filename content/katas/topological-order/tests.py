"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import topological_order


def test_orders_a_simple_chain() -> None:
    """Puts each name after the one it depends on."""
    assert topological_order({"c": ["b"], "b": ["a"], "a": []}) == ["a", "b", "c"]


def test_breaks_ties_alphabetically() -> None:
    """Chooses the alphabetically smallest name whenever several are ready."""
    assert topological_order({"z": [], "a": [], "m": []}) == ["a", "m", "z"]


def test_orders_a_diamond() -> None:
    """Puts a shared dependency before both of its dependents."""
    graph = {"top": ["left", "right"], "left": ["base"], "right": ["base"]}

    assert topological_order(graph) == ["base", "left", "right", "top"]


def test_refuses_a_cycle() -> None:
    """Returns None when no valid order exists."""
    assert topological_order({"a": ["b"], "b": ["a"]}) is None


def test_refuses_a_cycle_hidden_behind_a_valid_prefix() -> None:
    """Returns None for a graph that starts fine and ends in a cycle.

    A solution that emits names as it finds them and only then notices the
    cycle has to discard a partial answer -- returning the prefix is a wrong
    answer that looks plausible.
    """
    graph = {"a": [], "b": ["a"], "x": ["y"], "y": ["x"]}

    assert topological_order(graph) is None


def test_handles_an_empty_graph() -> None:
    """Returns an empty order for no names."""
    assert topological_order({}) == []


def test_includes_names_that_are_only_dependencies() -> None:
    """Includes a name that never appears as a key.

    `tools` has no entry of its own. A solution that orders only the dict's
    keys leaves it out of the answer entirely.
    """
    assert topological_order({"build": ["tools"]}) == ["tools", "build"]


def test_handles_independent_components() -> None:
    """Interleaves two unconnected parts of the graph by the tie-break.

    Both `a` and `c` are ready at the start. Emitting `a` makes `b` ready, and
    `b` sorts before `c`, so the second component waits -- the tie-break is
    over everything that is ready, not over one component at a time.
    """
    graph = {"b": ["a"], "d": ["c"]}

    assert topological_order(graph) == ["a", "b", "c", "d"]


def test_puts_every_dependency_before_its_dependent() -> None:
    """Respects a longer dependency chain through several names."""
    graph = {
        "app": ["lib", "config"],
        "lib": ["core"],
        "config": ["core"],
        "core": [],
    }
    order = topological_order(graph)

    assert order is not None
    assert order.index("core") < order.index("lib")
    assert order.index("lib") < order.index("app")
    assert order.index("config") < order.index("app")


def test_orders_a_large_graph_quickly() -> None:
    """Orders a graph far deeper than Python will recurse.

    Ten thousand names in a chain. Kahn's algorithm uses no recursion at all,
    which is most of the reason to reach for it.
    """
    length = 10_000
    graph = {f"n{index + 1:05d}": [f"n{index:05d}"] for index in range(length)}

    order = topological_order(graph)

    assert order is not None
    assert order[0] == "n00000"
    assert order[-1] == f"n{length:05d}"
