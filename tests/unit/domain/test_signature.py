"""A kata's signature: bounds that keep the author's spelling, and what is derived.

The renderings are the claim worth testing. The constraints list, the header and
the stub docstring are all produced here from the same fields, and the page
trusts that they agree because there is one place to disagree from.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from practice.domain.errors import InvalidValueError
from practice.domain.signature import (
    Bound,
    ClassSignature,
    Function,
    Parameter,
    Raises,
    Range,
    Returns,
    Signature,
    docstring_of,
)


def _range(low: int | str | None = None, high: int | str | None = None) -> Range:
    return Range(
        low=Bound.parse(low) if low is not None else None,
        high=Bound.parse(high) if high is not None else None,
    )


def _numbers(
    *,
    name: str = "numbers",
    type: str = "list[int]",  # noqa: A002
    description: str = "the values to check.",
    length: Range | None = None,
    item_length: Range | None = None,
    values: Range | None = None,
    nodes: Range | None = None,
) -> Parameter:
    return Parameter(
        name=name,
        type=type,
        description=description,
        length=length,
        item_length=item_length,
        values=values,
        nodes=nodes,
    )


def _function(*parameters: Parameter, name: str = "has_duplicate") -> Function:
    return Function(
        name=name,
        summary="Return whether any value appears more than once.",
        parameters=parameters,
        returns=Returns(type="bool", description="True if some value repeats."),
    )


# --- bounds ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        (5, 5),
        (-3, -3),
        ("10**5", 100_000),
        ("2 * 10**5", 200_000),
        ("-2**31", -(2**31)),
        ("2**31 - 1", 2**31 - 1),
        ("(3 + 4) * 2", 14),
        ("7 // 2", 3),
        ("+4", 4),
    ],
)
def test_a_bound_is_integer_arithmetic_that_keeps_its_spelling(
    raw: int | str, value: int
) -> None:
    bound = Bound.parse(raw)

    assert bound.value == value
    assert bound.text == str(raw)


@pytest.mark.parametrize(
    "raw",
    ["10 **", "__import__('os')", "1.5", "len(x)", "2**99999", "1 // 0", "'a'"],
)
def test_anything_but_integer_arithmetic_is_not_a_bound(raw: str) -> None:
    with pytest.raises(InvalidValueError):
        Bound.parse(raw)


def test_a_boolean_is_not_a_bound() -> None:
    with pytest.raises(InvalidValueError, match="not a boolean"):
        Bound.parse(True)


def test_a_range_needs_an_end_and_cannot_run_backwards() -> None:
    with pytest.raises(InvalidValueError, match="min, a max or both"):
        Range()
    with pytest.raises(InvalidValueError, match="down to"):
        _range(10, 1)


def test_a_range_contains_its_ends_and_nothing_past_them() -> None:
    both = _range(1, 3)
    assert [both.contains(n) for n in (0, 1, 3, 4)] == [False, True, True, False]
    assert _range(low=2).contains(10**9)
    assert not _range(low=2).contains(1)
    assert _range(high=2).contains(-(10**9))


def test_a_range_renders_whichever_ends_it_has() -> None:
    assert _range(0, "10**5").render("len(x)") == "0 <= len(x) <= 10**5"
    assert _range(low=1).render("k") == "k >= 1"
    assert _range(high="2 * 10**5").render("n") == "n <= 2 * 10**5"


# --- parameters --------------------------------------------------------------


@pytest.mark.parametrize("name", ["", "two words", "class", "1st"])
def test_a_parameter_is_named_like_a_python_argument(name: str) -> None:
    with pytest.raises(InvalidValueError, match="parameter name"):
        _numbers(name=name)


def test_a_parameter_needs_a_type_and_a_description() -> None:
    with pytest.raises(InvalidValueError, match="type"):
        _numbers(type=" ")
    with pytest.raises(InvalidValueError, match="description"):
        _numbers(description=" ")


@pytest.mark.parametrize(
    ("kind", "depth", "holds_nodes", "is_node"),
    [
        ("int", 0, False, False),
        ("list[int]", 1, False, False),
        ("list[list[int]]", 2, False, False),
        ("list[tuple[int, int]]", 2, False, False),
        ("tuple[int,int]", 1, False, False),
        ("TreeNode | None", 0, True, True),
        ("ListNode", 0, True, True),
        ("list[ListNode | None]", 1, True, False),
        ("str", 0, False, False),
    ],
)
def test_a_type_says_how_deep_it_is_and_whether_it_holds_nodes(
    kind: str, depth: int, holds_nodes: bool, is_node: bool
) -> None:
    parameter = _numbers(type=kind)

    assert (parameter.depth, parameter.holds_nodes, parameter.is_node) == (
        depth,
        holds_nodes,
        is_node,
    )


def test_a_parameter_renders_each_bound_it_declares_in_a_fixed_order() -> None:
    parameter = _numbers(
        values=_range("-10**9", "10**9"),
        length=_range(0, "10**6"),
        item_length=_range(0, 5),
    )

    assert [line for _, line in parameter.measures()] == [
        "0 <= len(numbers) <= 10**6",
        "0 <= len(numbers[i]) <= 5",
        "-10**9 <= numbers[i] <= 10**9",
    ]
    assert parameter.is_bounded


def test_the_value_subject_follows_the_shape_of_the_type() -> None:
    scalar = _numbers(name="n", type="int", values=_range(0, 9))
    grid = _numbers(name="matrix", type="list[list[int]]", values=_range(0, 9))
    tree = _numbers(name="root", type="TreeNode | None", values=_range(0, 9))
    nodes = _numbers(name="root", type="TreeNode | None", nodes=_range(0, 500))

    assert scalar.measures()[0][1] == "0 <= n <= 9"
    assert grid.measures()[0][1] == "0 <= matrix[i][j] <= 9"
    assert tree.measures()[0][1] == "0 <= node.value <= 9"
    assert nodes.measures()[0][1] == "0 <= the number of nodes in root <= 500"


def test_an_unbounded_parameter_says_so() -> None:
    assert not _numbers().is_bounded
    assert _numbers().measures() == ()


# --- callables ---------------------------------------------------------------


def test_a_return_may_leave_its_description_out_only_for_none() -> None:
    assert Returns(type="None").description is None
    with pytest.raises(InvalidValueError, match="must say what it returns"):
        Returns(type="bool")
    with pytest.raises(InvalidValueError, match="description"):
        Returns(type="bool", description=" ")
    with pytest.raises(InvalidValueError, match="type"):
        Returns(type=" ")


def test_a_raises_entry_names_an_exception_and_says_when() -> None:
    assert Raises(type="ValueError", description="if empty").type == "ValueError"
    with pytest.raises(InvalidValueError, match="exception name"):
        Raises(type="not valid", description="x")
    with pytest.raises(InvalidValueError, match="description"):
        Raises(type="ValueError", description=" ")


def test_a_function_renders_the_call_line_the_header_opens_with() -> None:
    function = _function(_numbers(), _numbers(name="limit", type="int"))

    assert function.call == "has_duplicate(numbers: list[int], limit: int) -> bool"


def test_a_function_repeating_a_parameter_or_missing_its_return_is_refused() -> None:
    with pytest.raises(InvalidValueError, match="repeats a parameter"):
        _function(_numbers(), _numbers())
    with pytest.raises(InvalidValueError, match="must say what it returns"):
        Function(name="f", summary="Do it.")
    with pytest.raises(InvalidValueError, match="summary"):
        Function(name="__init__", summary=" ")
    with pytest.raises(InvalidValueError, match="details"):
        Function(name="__init__", summary="Do it.", details=" ")


def test_a_constructor_has_no_return_and_its_call_has_no_arrow() -> None:
    constructor = Function(name="__init__", summary="Create an empty store.")

    assert constructor.call == "__init__()"


def test_a_class_needs_methods_and_cannot_repeat_one() -> None:
    method = Function(name="__init__", summary="Create it.")
    assert ClassSignature(name="Store", summary="A store.", methods=(method,)).methods
    with pytest.raises(InvalidValueError, match="no methods"):
        ClassSignature(name="Store", summary="A store.", methods=())
    with pytest.raises(InvalidValueError, match="repeats a method"):
        ClassSignature(name="Store", summary="A store.", methods=(method, method))
    with pytest.raises(InvalidValueError, match="class name"):
        ClassSignature(name="not valid", summary="A store.", methods=(method,))
    with pytest.raises(InvalidValueError, match="summary"):
        ClassSignature(name="Store", summary=" ", methods=(method,))


# --- the signature -----------------------------------------------------------


def test_a_signature_declares_something_once() -> None:
    function = _function()
    with pytest.raises(InvalidValueError, match="a function or a class"):
        Signature()
    with pytest.raises(InvalidValueError, match="same name twice"):
        Signature(functions=(function, function))
    with pytest.raises(InvalidValueError, match="note cannot be blank"):
        Signature(functions=(function,), notes=(" ",))


def _store() -> Signature:
    word = Parameter(
        name="word",
        type="str",
        description="the word.",
        length=_range(0, 20),
    )
    add = Function(
        name="add",
        summary="Store it.",
        parameters=(word,),
        returns=Returns(type="None"),
    )
    search = Function(
        name="search",
        summary="Look it up.",
        parameters=(replace(word, length=_range(0, 20)),),
        returns=Returns(type="bool", description="True if found."),
    )
    return Signature(
        classes=(
            ClassSignature(
                name="Store",
                summary="A store.",
                methods=(Function(name="__init__", summary="Create."), add, search),
            ),
        ),
        notes=("Words are lowercase.",),
    )


def test_callables_are_listed_with_the_class_they_belong_to() -> None:
    signature = _store()
    plain = Signature(functions=(_function(),))

    assert [(owner, f.name) for owner, f in signature.callables()] == [
        ("Store", "__init__"),
        ("Store", "add"),
        ("Store", "search"),
    ]
    assert [(owner, f.name) for owner, f in plain.callables()] == [
        (None, "has_duplicate")
    ]


def test_a_shared_bound_is_printed_once_and_the_notes_follow() -> None:
    assert _store().constraints() == (
        "0 <= len(word) <= 20",
        "Words are lowercase.",
    )


def test_a_bound_two_methods_disagree_about_is_printed_per_method() -> None:
    signature = _store()
    store = signature.classes[0]
    search = replace(
        store.methods[2],
        parameters=(replace(store.methods[2].parameters[0], length=_range(0, 5)),),
    )
    changed = replace(
        signature,
        classes=(replace(store, methods=(*store.methods[:2], search)),),
    )

    assert changed.constraints() == (
        "Store.add: 0 <= len(word) <= 20",
        "Store.search: 0 <= len(word) <= 5",
        "Words are lowercase.",
    )


def test_a_functions_prefix_is_its_own_name() -> None:
    first = _function(_numbers(length=_range(0, 5)), name="first")
    second = _function(_numbers(length=_range(0, 9)), name="second")

    assert Signature(functions=(first, second)).constraints() == (
        "first: 0 <= len(numbers) <= 5",
        "second: 0 <= len(numbers) <= 9",
    )


def test_the_header_text_lists_inputs_and_outputs_and_skips_a_bare_constructor() -> (
    None
):
    assert _store().header_text() == (
        "Store.add(word: str) -> None\n"
        "  Input:\n"
        "    word: str -- the word.\n"
        "  Output: None\n"
        "\n"
        "Store.search(word: str) -> bool\n"
        "  Input:\n"
        "    word: str -- the word.\n"
        "  Output: bool -- True if found."
    )


def test_a_constructor_with_parameters_is_part_of_the_header() -> None:
    constructor = Function(
        name="__init__",
        summary="Create it.",
        parameters=(_numbers(name="k", type="int"),),
    )
    signature = Signature(
        classes=(ClassSignature(name="Top", summary="Top.", methods=(constructor,)),)
    )

    assert signature.header_text() == (
        "Top.__init__(k: int)\n  Input:\n    k: int -- the values to check."
    )


# --- the docstring -----------------------------------------------------------


def test_a_docstring_is_generated_in_the_google_sections_the_stubs_use() -> None:
    function = Function(
        name="median",
        summary="Return the median.",
        details="Taken over everything added so far.",
        parameters=(_numbers(name="value", type="int", description="the number."),),
        returns=Returns(type="float", description="The middle value."),
        raises=(Raises(type="ValueError", description="if nothing was added."),),
    )

    assert docstring_of(function.summary, function, indent=4) == (
        "Return the median.\n"
        "\n"
        "Taken over everything added so far.\n"
        "\n"
        "Args:\n"
        "    value: the number.\n"
        "\n"
        "Returns:\n"
        "    The middle value.\n"
        "\n"
        "Raises:\n"
        "    ValueError: if nothing was added."
    )


def test_a_none_return_and_a_summary_only_class_have_no_sections() -> None:
    function = Function(name="add", summary="Store it.", returns=Returns(type="None"))

    assert docstring_of(function.summary, function, indent=8) == "Store it."
    assert docstring_of("A store.", None, indent=4) == "A store."


def test_a_long_description_wraps_under_its_own_name() -> None:
    long = "the values to check, " + "and then some more words " * 8
    function = _function(_numbers(description=long.strip()))

    text = docstring_of(function.summary, function, indent=4)
    lines = text.splitlines()
    start = lines.index("Args:")

    assert lines[start + 1].startswith("    numbers: the values")
    assert lines[start + 2].startswith("        ")
    assert all(len(line) + 4 <= 79 for line in lines)
