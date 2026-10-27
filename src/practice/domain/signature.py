"""A kata's callable surface, as fields: names, types, ranges, and what they mean.

Before Phase 28 a kata said what it took and gave in three places that nothing
tied together -- the stub's docstring, the prose prompt and a free-text
`constraints:` list. Per ADR 0022 the third was the dangerous one: a constraint
is a promise about the inputs the hidden suite passes, and a new test that
stepped outside a stated bound failed nothing. This module makes the promise a
value that other code can hold a suite to (`tests/content/test_bounds.py`) and
the page can draw the same way every time.

**One structure, three renderings.** The page's Input / Output header, the
constraints list and the stub's docstring are all *derived* from a `Signature`
here, in this module, so they cannot disagree with each other or with the
declaration. The alternative that was rejected is a parser that reads
constraints back out of prose: it works on the 270 lines that happen to be
phrased `lo <= len(x) <= hi` and is silently wrong about the rest, which is the
failure ADR 0022 is about.

**Four measures, and the line drawn under them.** A parameter can be bounded by
its `length`, by the length of each of its elements (`item_length`), by the
integers it holds (`values`) or by the nodes reachable from it (`nodes`). That
is what the hidden suites' bounds actually were, measured across all 245
katas -- not a general constraint language. Whatever does not fit a range ("all
values are distinct", "at most 2 * 10**5 calls") stays a note, and a note is
honest about being unchecked: the page prints it, nothing enforces it.

**Bounds keep the author's spelling.** `Bound` holds the value to compare
against *and* the text to print, because `2 * 10**5` is how a person writes a
size and `200000` is what a person has to decode. The value is computed by a
tiny arithmetic evaluator rather than `eval`, so a typo in a bound cannot run
code and the domain stays free of it.
"""

from __future__ import annotations

import ast
import keyword
import re
import textwrap
from dataclasses import dataclass, field
from typing import Final

from practice.domain.errors import InvalidValueError

__all__ = [
    "Bound",
    "ClassSignature",
    "Function",
    "Parameter",
    "Raises",
    "Range",
    "Returns",
    "Signature",
    "docstring_of",
]

#: Wrapping width for a generated docstring, counted from the left margin of the
#: file, so a method's docstring wraps four columns sooner than a function's.
#: Narrower than `ruff`'s 88, deliberately: 79 is what the first 245 stubs were
#: hand-wrapped to, so regenerating them moved only the lines that had to move.
LINE_LENGTH: Final = 79

#: Past this a `**` is a way to hang the validator, not a size.
_MAX_EXPONENT: Final = 10_000

#: Names the `nodes` and `values` measures walk through. Spelled out here and in
#: the probe that enforces them (`tests/content/bounds_probe.py`); the two lists
#: are the same fact, and a test holds them to it.
NODE_LINKS: Final = ("left", "right", "next", "neighbours")

#: Container prefixes of a type string, outermost first. Used only to decide how
#: many indices to print (`matrix[i][j]`), never to check anything.
_CONTAINERS: Final = (
    "list[",
    "tuple[",
    "set[",
    "frozenset[",
    "Sequence[",
    "Iterable[",
    "dict[",
    "Mapping[",
)
_BUILTIN_SCALARS: Final = frozenset({"int", "str", "bool", "float", "bytes"})


def _evaluate(node: ast.expr) -> int:  # noqa: PLR0911
    match node:
        case ast.Constant(value=int() as value) if not isinstance(value, bool):
            return int(value)
        case ast.UnaryOp(op=ast.USub(), operand=operand):
            return -_evaluate(operand)
        case ast.UnaryOp(op=ast.UAdd(), operand=operand):
            return _evaluate(operand)
        case ast.BinOp(left=left, op=ast.Add(), right=right):
            return _evaluate(left) + _evaluate(right)
        case ast.BinOp(left=left, op=ast.Sub(), right=right):
            return _evaluate(left) - _evaluate(right)
        case ast.BinOp(left=left, op=ast.Mult(), right=right):
            return _evaluate(left) * _evaluate(right)
        case ast.BinOp(left=left, op=ast.FloorDiv(), right=right):
            divisor = _evaluate(right)
            if divisor == 0:
                raise InvalidValueError("a bound cannot divide by zero")
            return _evaluate(left) // divisor
        case ast.BinOp(left=left, op=ast.Pow(), right=right):
            exponent = _evaluate(right)
            if not 0 <= exponent <= _MAX_EXPONENT:
                raise InvalidValueError(
                    f"a bound's exponent must be between 0 and {_MAX_EXPONENT}"
                )
            return int(_evaluate(left) ** exponent)
        case _:
            raise InvalidValueError(
                "a bound is integer arithmetic: numbers, + - * // ** and brackets"
            )


@dataclass(frozen=True, slots=True)
class Bound:
    """One end of a range: the integer to compare against and how it is written."""

    text: str
    value: int

    @classmethod
    def parse(cls, raw: int | str) -> Bound:
        """`10**5`, `2 * 10**5` and `-2**31` are all bounds; so is a plain int."""
        if isinstance(raw, bool):
            raise InvalidValueError("a bound is a number, not a boolean")
        if isinstance(raw, int):
            return cls(text=str(raw), value=raw)
        text = raw.strip()
        try:
            tree = ast.parse(text, mode="eval")
        except SyntaxError as exc:
            raise InvalidValueError(f"{raw!r} is not a bound: {exc.msg}") from exc
        return cls(text=text, value=_evaluate(tree.body))


@dataclass(frozen=True, slots=True)
class Range:
    """An inclusive range with either end optional.

    Inclusive only. Every strict bound in the library was an inclusive one in
    disguise (`n < 2**2000` is `n <= 2**2000 - 1`), and a second kind of end
    would double the renderings for no bound that needs it.
    """

    low: Bound | None = None
    high: Bound | None = None

    def __post_init__(self) -> None:
        if self.low is None and self.high is None:
            raise InvalidValueError("a range needs a min, a max or both")
        if (
            self.low is not None
            and self.high is not None
            and self.low.value > self.high.value
        ):
            raise InvalidValueError(
                f"a range cannot run from {self.low.text} down to {self.high.text}"
            )

    def contains(self, number: int) -> bool:
        if self.low is not None and number < self.low.value:
            return False
        return self.high is None or number <= self.high.value

    def render(self, subject: str) -> str:
        """`0 <= len(x) <= 10**5`, or one half of it when the other is open."""
        if self.low is not None and self.high is not None:
            return f"{self.low.text} <= {subject} <= {self.high.text}"
        if self.low is not None:
            return f"{subject} >= {self.low.text}"
        return f"{subject} <= {self.high.text if self.high else ''}"


def _require_name(value: str, *, what: str) -> None:
    if not value.isidentifier() or keyword.iskeyword(value):
        raise InvalidValueError(f"{value!r} is not a valid {what}")


def _require_text(value: str, *, what: str) -> None:
    if not value.strip():
        raise InvalidValueError(f"{what} cannot be blank")


@dataclass(frozen=True, slots=True)
class Parameter:
    """One argument a kata's callable takes, with the bounds the suite keeps to."""

    name: str
    type: str
    description: str
    length: Range | None = None
    item_length: Range | None = None
    values: Range | None = None
    nodes: Range | None = None

    def __post_init__(self) -> None:
        _require_name(self.name, what="parameter name")
        _require_text(self.type, what="a parameter's type")
        _require_text(self.description, what="a parameter's description")

    def _innermost(self) -> tuple[int, str]:
        """The element type under every container, and how many there were."""
        remaining = self.type.replace(" ", "")
        depth = 0
        while True:
            prefix = next((p for p in _CONTAINERS if remaining.startswith(p)), None)
            if prefix is None:
                break
            depth += 1
            remaining = remaining[len(prefix) :]
        # The first name left once the containers are peeled: up to the next
        # bracket, comma or union bar, so `int,int]]` is `int` and
        # `Node|None` is `Node`.
        bare = re.split(r"[\],|]", remaining.removeprefix("None|"))[0]
        return depth, bare

    @property
    def depth(self) -> int:
        """How many containers wrap the scalars in `type`: 0 for an `int`."""
        return self._innermost()[0]

    @property
    def holds_nodes(self) -> bool:
        """Whether the elements are linked nodes rather than builtin scalars.

        Decided from the annotation alone, which is all the declaration has: a
        kata's `ListNode` and `TreeNode` are its own classes (CLAUDE.md), so
        there is no shared type to test against. Anything that is not a
        builtin scalar is a node, and a container of them -- `lists` in a merge
        of k sorted lists -- holds nodes too.
        """
        return self._innermost()[1] not in _BUILTIN_SCALARS

    @property
    def is_node(self) -> bool:
        """A single linked structure, as opposed to a container of them."""
        return self.depth == 0 and self.holds_nodes

    def measures(self) -> tuple[tuple[str, str], ...]:
        """Each bound as `(subject, rendered line)`, in a fixed order.

        The subject is kept beside the line so that two methods bounding the
        same expression differently can be told apart without parsing the line
        back apart.
        """
        found: list[tuple[str, str]] = []
        if self.length is not None:
            subject = f"len({self.name})"
            found.append((subject, self.length.render(subject)))
        if self.item_length is not None:
            subject = f"len({self.name}[i])"
            found.append((subject, self.item_length.render(subject)))
        if self.values is not None:
            subject = self._value_subject()
            found.append((subject, self.values.render(subject)))
        if self.nodes is not None:
            subject = f"the number of nodes in {self.name}"
            found.append((subject, self.nodes.render(subject)))
        return tuple(found)

    def _value_subject(self) -> str:
        if self.holds_nodes:
            return "node.value"
        return self.name + "".join(f"[{'ijk'[min(i, 2)]}]" for i in range(self.depth))

    @property
    def is_bounded(self) -> bool:
        return any((self.length, self.item_length, self.values, self.nodes))


@dataclass(frozen=True, slots=True)
class Returns:
    """What comes back. The description may be left out only for `None`.

    A callable that returns `None` has nothing to describe, and a `Returns:`
    section reading "Nothing." in forty stubs is noise a solver learns to skip.
    Every other type needs its sentence: "a `bool`" is not a statement of what
    `True` means.
    """

    type: str
    description: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.type, what="a return type")
        if self.description is None:
            if self.type.strip() != "None":
                raise InvalidValueError(
                    f"a callable returning {self.type} must say what it returns"
                )
        else:
            _require_text(self.description, what="a return description")


@dataclass(frozen=True, slots=True)
class Raises:
    type: str
    description: str

    def __post_init__(self) -> None:
        _require_name(self.type, what="exception name")
        _require_text(self.description, what="a raises description")


@dataclass(frozen=True, slots=True)
class Function:
    """A function or a method the tests call.

    `returns` is `None` for `__init__` and nothing else: every other callable a
    kata asks for gives something back, and one that gives `None` says so in its
    `type` rather than by leaving the field out, so the header always has an
    Output line.
    """

    name: str
    summary: str
    parameters: tuple[Parameter, ...] = ()
    returns: Returns | None = None
    details: str | None = None
    raises: tuple[Raises, ...] = ()

    def __post_init__(self) -> None:
        _require_name(self.name, what="function name")
        _require_text(self.summary, what="a summary")
        if self.details is not None:
            _require_text(self.details, what="details")
        names = [parameter.name for parameter in self.parameters]
        if len(set(names)) != len(names):
            raise InvalidValueError(f"{self.name} repeats a parameter")
        if self.returns is None and self.name != "__init__":
            raise InvalidValueError(f"{self.name} must say what it returns")

    @property
    def call(self) -> str:
        """`name(a: int, b: str) -> bool`, the line the header opens with."""
        arguments = ", ".join(f"{p.name}: {p.type}" for p in self.parameters)
        returned = f" -> {self.returns.type}" if self.returns else ""
        return f"{self.name}({arguments}){returned}"


@dataclass(frozen=True, slots=True)
class ClassSignature:
    """A class the tests construct, and the methods they call on it."""

    name: str
    summary: str
    methods: tuple[Function, ...]

    def __post_init__(self) -> None:
        _require_name(self.name, what="class name")
        _require_text(self.summary, what="a summary")
        if not self.methods:
            raise InvalidValueError(f"class {self.name} declares no methods")
        names = [method.name for method in self.methods]
        if len(set(names)) != len(names):
            raise InvalidValueError(f"class {self.name} repeats a method")


@dataclass(frozen=True, slots=True)
class Signature:
    """Everything a kata's tests import, and everything they may pass in.

    Functions and classes can sit side by side: serialising a tree asks for two
    functions, and one variant asks for a function and a class.
    """

    functions: tuple[Function, ...] = ()
    classes: tuple[ClassSignature, ...] = ()
    notes: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.functions and not self.classes:
            raise InvalidValueError("a signature declares a function or a class")
        names = [function.name for function in self.functions]
        names += [cls.name for cls in self.classes]
        if len(set(names)) != len(names):
            raise InvalidValueError("a signature declares the same name twice")
        if any(not note.strip() for note in self.notes):
            raise InvalidValueError("a note cannot be blank")

    def callables(self) -> tuple[tuple[str | None, Function], ...]:
        """Every callable with the class it belongs to, in declaration order."""
        found: list[tuple[str | None, Function]] = [(None, f) for f in self.functions]
        for cls in self.classes:
            found.extend((cls.name, method) for method in cls.methods)
        return tuple(found)

    def header_text(self) -> str:
        """The Input / Output block as plain text, for the terminal and the tutor.

        The page draws the same facts from the same fields with markup; this is
        the version for the surfaces that have none, kept here so that the two
        cannot be edited apart.
        """
        blocks: list[str] = []
        for owner, function in self.callables():
            if function.name == "__init__" and not function.parameters:
                continue
            call = f"{owner}.{function.call}" if owner else function.call
            lines = [call]
            if function.parameters:
                lines.append("  Input:")
                lines.extend(
                    f"    {p.name}: {p.type} -- {p.description}"
                    for p in function.parameters
                )
            if function.returns is not None:
                text = function.returns.description
                suffix = f" -- {text}" if text else ""
                lines.append(f"  Output: {function.returns.type}{suffix}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def constraints(self) -> tuple[str, ...]:
        """The constraints list the page prints: ranges first, then the notes.

        A parameter two methods share (`word`, in `add` and `search`) is printed
        once when both give it the same range, which is the common case, and
        once per method, prefixed, when they differ -- a bound listed once
        would be wrong about one of them.
        """
        rendered: dict[str, set[str]] = {}
        for _, function in self.callables():
            for parameter in function.parameters:
                for subject, line in parameter.measures():
                    rendered.setdefault(subject, set()).add(line)
        lines: list[str] = []
        for owner, function in self.callables():
            qualified = f"{owner}.{function.name}" if owner else function.name
            for parameter in function.parameters:
                for subject, line in parameter.measures():
                    shown = (
                        f"{qualified}: {line}" if len(rendered[subject]) > 1 else line
                    )
                    if shown not in lines:
                        lines.append(shown)
        lines.extend(self.notes)
        return tuple(lines)


# --- the docstring ---------------------------------------------------------


def _wrap(text: str, *, indent: int, first: str = "", rest: str = "") -> list[str]:
    """`text` reflowed to the line length, `indent` columns in from the margin."""
    return textwrap.wrap(
        " ".join(text.split()),
        width=LINE_LENGTH - indent,
        initial_indent=first,
        subsequent_indent=rest,
        break_long_words=False,
        break_on_hyphens=False,
    )


def docstring_of(summary: str, function: Function | None, *, indent: int) -> str:
    """A docstring's cleaned text, the way `inspect.cleandoc` would give it back.

    `indent` is the column the docstring's text starts in, so a method wraps
    where its file wraps. The *details* are emitted as they were written: they
    carry the lists and the aligned examples that a reflow would flatten, and
    unlike the summary and the descriptions they are never repeated anywhere
    else on the page.
    """
    # Three columns narrower than the rest: the first line carries the opening
    # quotes, and a one-liner carries the closing ones, and neither may push the
    # line past the margin.
    blocks: list[str] = ["\n".join(_wrap(summary, indent=indent + 3))]
    if function is None:
        return blocks[0]
    if function.details is not None:
        blocks.append(function.details.strip("\n"))
    if function.parameters:
        lines = ["Args:"]
        for parameter in function.parameters:
            lines += _wrap(
                parameter.description,
                indent=indent,
                first=f"    {parameter.name}: ",
                rest="        ",
            )
        blocks.append("\n".join(lines))
    if function.returns is not None and function.returns.description is not None:
        lines = ["Returns:"]
        lines += _wrap(
            function.returns.description, indent=indent, first="    ", rest="    "
        )
        blocks.append("\n".join(lines))
    if function.raises:
        lines = ["Raises:"]
        for raised in function.raises:
            lines += _wrap(
                raised.description,
                indent=indent,
                first=f"    {raised.type}: ",
                rest="        ",
            )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
