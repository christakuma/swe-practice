"""The bounds checker can fail -- and fails on the right thing.

`test_katas.py` arms the checker on every reference and expects a pass, which
proves only that the hidden suites keep inside their declared ranges. A checker
that never raised would pass it just as well, which is ADR 0022's point about
any test of this shape: *a check you have not watched fail is a guess*. So this
file feeds the checker the cases it exists for and reads what it says.

In-process, no subprocess: the footer is plain Python, and `bounded_source`
returns text that can be executed here exactly as the graded process executes
it. That is the point of building it as text.
"""

from __future__ import annotations

import inspect
import sys
import tracemalloc
from dataclasses import replace
from typing import Any

import pytest

from practice.adapters.content import load_exercise
from practice.config import content_root
from practice.domain.exercise import KataSpec
from practice.domain.signature import (
    NODE_LINKS,
    Bound,
    ClassSignature,
    Function,
    Parameter,
    Range,
    Returns,
    Signature,
)
from tests.content import bounds_probe
from tests.content.bounds_probe import bounded_source


def _range(low: int | None = None, high: int | None = None) -> Range:
    return Range(
        low=Bound.parse(low) if low is not None else None,
        high=Bound.parse(high) if high is not None else None,
    )


def _signature(parameter: Parameter, name: str = "f") -> Signature:
    return Signature(
        functions=(
            Function(
                name=name,
                summary="Do it.",
                parameters=(parameter,),
                returns=Returns(type="int", description="A number."),
            ),
        )
    )


def _armed(source: str, signature: Signature) -> dict[str, Any]:
    namespace: dict[str, Any] = {"__name__": "solution"}
    exec(compile(bounded_source(source, signature), "solution.py", "exec"), namespace)  # noqa: S102
    return namespace


NUMBERS = Parameter(name="numbers", type="list[int]", description="The values.")
IDENTITY = "def f(numbers):\n    return len(numbers)\n"


def test_the_footer_adds_no_name_to_the_module_it_arms() -> None:
    plain: dict[str, Any] = {"__name__": "solution"}
    exec(compile(IDENTITY, "solution.py", "exec"), plain)  # noqa: S102
    armed = _armed(IDENTITY, _signature(NUMBERS))

    assert set(armed) == set(plain)


def test_a_call_inside_its_bounds_is_untouched() -> None:
    signature = _signature(replace(NUMBERS, length=_range(0, 3), values=_range(0, 9)))

    assert _armed(IDENTITY, signature)["f"]([1, 2, 3]) == 3


@pytest.mark.parametrize(
    ("parameter", "argument", "complaint"),
    [
        (
            replace(NUMBERS, length=_range(0, 3)),
            [1, 2, 3, 4],
            "length 4 is outside 0..3",
        ),
        (
            replace(NUMBERS, values=_range(0, 9)),
            [1, [2, 10]],
            "value 10 is outside 0..9",
        ),
        (replace(NUMBERS, values=_range(0, 9)), [-1], "value -1 is outside 0..9"),
        (
            replace(NUMBERS, item_length=_range(1, 2)),
            [[1], []],
            "an element has length 0",
        ),
    ],
)
def test_a_call_outside_a_declared_bound_names_the_argument_and_the_range(
    parameter: Parameter, argument: object, complaint: str
) -> None:
    signature = _signature(parameter)

    with pytest.raises(AssertionError, match="DECLARED BOUND BROKEN") as raised:
        _armed(IDENTITY, signature)["f"](argument)

    assert "f(numbers)" in str(raised.value)
    assert complaint in str(raised.value)


def test_an_open_ended_range_still_checks_the_end_it_has() -> None:
    signature = _signature(replace(NUMBERS, length=_range(low=2)))

    with pytest.raises(AssertionError, match=r"outside 2\.\.inf"):
        _armed(IDENTITY, signature)["f"]([1])


def test_only_the_outermost_call_is_checked() -> None:
    """A recursive reference hands its own sub-problems back through the name."""
    source = "def f(numbers):\n    return 0 if not numbers else 1 + f(numbers[1:])\n"
    signature = _signature(replace(NUMBERS, length=_range(low=2)))

    assert _armed(source, signature)["f"]([5, 6, 7]) == 3


def test_the_depth_is_restored_after_a_call_that_raised() -> None:
    signature = _signature(replace(NUMBERS, length=_range(0, 1)))
    armed = _armed("def f(numbers):\n    raise KeyError\n", signature)

    with pytest.raises(KeyError):
        armed["f"]([1])
    with pytest.raises(AssertionError, match="DECLARED BOUND BROKEN"):
        armed["f"]([1, 2])


def test_a_list_that_raises_when_iterated_is_measured_without_being_iterated() -> None:
    """`Tripwire` and `Watched` prove an early return by objecting to a look."""

    class Tripwire(list[int]):
        def __iter__(self) -> Any:
            raise AssertionError("iterated")

        def __getitem__(self, index: Any) -> Any:
            raise AssertionError("indexed")

        def __len__(self) -> int:
            raise AssertionError("measured")

    signature = _signature(replace(NUMBERS, length=_range(0, 9), values=_range(0, 9)))

    assert _armed("def f(numbers):\n    return 1\n", signature)["f"](Tripwire([1, 2]))


def test_a_parameter_the_call_omitted_is_not_a_violation() -> None:
    signature = _signature(replace(NUMBERS, length=_range(0, 1)))
    armed = _armed("def f(numbers=()):\n    return 0\n", signature)

    assert armed["f"]() == 0


NODE = Parameter(name="root", type="Node | None", description="The root.")
NODES = """
class Node:
    def __init__(self, value, next=None, left=None):
        self.value, self.next, self.left = value, next, left


def f(root):
    return 1
"""


def test_nodes_are_counted_by_following_the_links_once_each() -> None:
    signature = _signature(replace(NODE, nodes=_range(0, 2), values=_range(0, 9)))
    namespace = _armed(NODES, signature)
    node = namespace["Node"]
    last = node(1)
    cycle = node(2, next=last)
    last.next = cycle  # a list that loops: still two nodes

    assert namespace["f"](cycle) == 1
    assert namespace["f"](None) == 1
    with pytest.raises(AssertionError, match=r"3 nodes is outside 0\.\.2"):
        namespace["f"](node(1, next=node(2, left=node(3))))
    with pytest.raises(AssertionError, match=r"node.value 10 is outside 0..9"):
        namespace["f"](node(10))


def test_a_container_of_nodes_is_followed_from_each_element() -> None:
    parameter = Parameter(name="root", type="list[Node | None]", description="x")
    signature = _signature(replace(parameter, values=_range(0, 9)))
    namespace = _armed(NODES, signature)
    node = namespace["Node"]

    assert namespace["f"]([node(1), None, node(2, next=node(3))]) == 1
    with pytest.raises(AssertionError, match=r"node.value 12 is outside"):
        namespace["f"]([node(1), node(5, next=node(12))])


def test_a_methods_arguments_are_checked_and_its_self_is_not() -> None:
    word = Parameter(name="word", type="str", description="x", length=_range(0, 3))
    add = Function(
        name="add",
        summary="Add.",
        parameters=(word,),
        returns=Returns(type="None"),
    )
    signature = Signature(
        classes=(ClassSignature(name="Store", summary="A store.", methods=(add,)),)
    )
    source = "class Store:\n    def add(self, word):\n        self.last = word\n"
    store = _armed(source, signature)["Store"]()

    store.add("abc")
    assert store.last == "abc"
    with pytest.raises(AssertionError, match=r"Store.add\(word\): length 4"):
        store.add("abcd")


def test_the_probe_follows_the_same_links_as_the_domain_names() -> None:
    """`NODE_LINKS` is the same fact in two files; this holds them together."""
    assert bounds_probe._NODE_LINKS == NODE_LINKS


def test_a_real_katas_reference_is_held_to_a_tightened_bound() -> None:
    """The whole path on a shipped kata: declare a bound the suite exceeds."""
    directory = content_root() / "katas" / "contains-a-duplicate"
    exercise = load_exercise(directory)
    assert isinstance(exercise.spec, KataSpec)
    assert exercise.spec.signature is not None
    function = exercise.spec.signature.functions[0]
    tight = replace(
        function,
        parameters=(replace(function.parameters[0], length=_range(0, 3)),),
    )
    source = (directory / exercise.spec.reference).read_text(encoding="utf-8")

    armed = _armed(source, replace(exercise.spec.signature, functions=(tight,)))

    assert armed[function.name]([1, 2, 1]) is True
    with pytest.raises(AssertionError, match=r"length 4 is outside 0\.\.3"):
        armed[function.name]([1, 2, 3, 4])


def test_a_recursive_reference_keeps_all_of_its_stack() -> None:
    """The check must not change how deep the answer can go.

    A wrapper between a function and its own recursive calls doubles the frames
    per level; `inverts-a-deep-tree` found this by overflowing at half the depth
    its reference survives. The outermost call runs the raw function instead.
    """
    source = "def f(numbers):\n    return 0 if not numbers else 1 + f(numbers[1:])\n"
    signature = _signature(replace(NUMBERS, length=_range(0, 10**9)))
    depth = sys.getrecursionlimit() - len(inspect.stack()) - 50

    assert _armed(source, signature)["f"]([0] * depth) == depth


def test_a_million_integers_are_checked_without_a_copy_of_them() -> None:
    """The suites that measure a solution's allocations run the probe inside
    their window; it may cost a few kilobytes and not the argument's size.
    """
    numbers = list(range(10**6))
    spec = {"values": [0, 10**6], "length": [0, 10**6]}
    tracemalloc.start()
    try:
        assert bounds_probe.problems("f(numbers)", numbers, spec) == []
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert peak < 50_000


def test_nested_integers_are_found_and_the_furthest_offender_is_named() -> None:
    spec = {"values": [0, 10]}
    found = bounds_probe.problems("f(x)", [[1, 2], (3, [4, -7]), [99, 5]], spec)

    assert found == ["f(x): value 99 is outside 0..10"]


def test_the_same_argument_is_looked_at_once() -> None:
    """A search called a thousand times on one list must stay a search.

    The cost of this is a same-length mutation between two calls that nobody
    makes: the second look is skipped, so a bound is missed and never invented.
    """
    signature = _signature(replace(NUMBERS, values=_range(0, 9)))
    f = _armed(IDENTITY, signature)["f"]
    numbers = [1, 2, 3]

    assert f(numbers) == 3
    numbers[0] = 10**6  # same object, same length: not looked at again
    assert f(numbers) == 3
    with pytest.raises(AssertionError, match="value 1000000"):
        f([10**6, 2, 3])  # a new object is a new look


def test_a_freed_list_s_address_does_not_excuse_the_next_one() -> None:
    """`id()` is reused once a list is freed, and a same-length list reuses it.

    The memo used to be keyed on `(id(argument), length)`, so a literal that
    landed on its predecessor's address skipped the check; this called the
    out-of-range list three times out of three and missed it every time.
    """
    signature = _signature(replace(NUMBERS, values=_range(0, 9)))
    f = _armed(IDENTITY, signature)["f"]

    for _ in range(3):
        assert f([1, 2, 3]) == 3
        with pytest.raises(AssertionError, match="value 99"):
            f([1, 2, 99])


@pytest.mark.parametrize("container", [tuple, set, frozenset])
def test_children_held_in_any_builtin_container_are_reached(
    container: type,
) -> None:
    signature = _signature(replace(NODE, nodes=_range(0, 2), values=_range(0, 9)))
    source = NODES.replace(
        "self.left = value, next, left",
        "self.left = value, next, left; self.neighbours = ()",
    )
    namespace = _armed(source, signature)
    node = namespace["Node"]

    root = node(1)
    root.neighbours = container([node(12)])
    with pytest.raises(AssertionError, match=r"node.value 12 is outside 0..9"):
        namespace["f"](root)

    crowded = node(1)
    crowded.neighbours = container([node(2), node(3)])
    with pytest.raises(AssertionError, match=r"3 nodes is outside 0\.\.2"):
        namespace["f"](crowded)
