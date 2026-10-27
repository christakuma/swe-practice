# ruff: noqa: PLR0911, PLR0912, PLR2004, PLW2901, S101
"""Draft every kata's structured signature from its stub and its constraint strings.

Run once, as Phase 28's migration, and kept so the finding it made can be read:

    uv run python tools/migrate_katas.py            # the report, writes nothing
    uv run python tools/migrate_katas.py --write    # rewrites exercise.yaml and stub.py

**The migration is finished; `--stubs` is the part that stays in use.** Once a
kata has a `signature:` the stub's docstrings are derived from it
(`test_its_stub_docstrings_are_generated_from_the_signature`), and after editing
the YAML this regenerates them rather than leaving an author to re-type text
the test then compares byte for byte:

    uv run python tools/migrate_katas.py --stubs            # every kata
    uv run python tools/migrate_katas.py --stubs two-sum    # one, by slug

**It drafts; a person reviews.** The stub gives it names, annotations and the
docstring's `Args:` and `Returns:`. The constraint strings give it ranges, and
only where a string says exactly one thing in exactly one of three shapes --
`lo <= len(x) <= hi`, `lo <= x[i] <= hi` and `lo <= x <= hi` -- or one of the
node-count sentences the tree and list katas share. Anything else becomes a
`notes:` line verbatim, which is the safe failure: the page still prints it and
nothing enforces it, exactly as before. A regex that is *confident about a
constraint it misread* would be the opposite failure (a bound the hidden suite
is held to that the author never wrote), so every pattern here is anchored and
there is no fuzzy matching.

It exits non-zero while any kata is flagged, which is the "no hand-edit flag
left" exit criterion of PLAN.md §11, Phase 28.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import sys
import textwrap
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Final

import yaml

from practice.adapters.content import load_exercise
from practice.config import content_root
from practice.domain.errors import InvalidValueError
from practice.domain.exercise import KataSpec
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

if TYPE_CHECKING:
    from pathlib import Path

_BOUND: Final = r"[-\d][\d *+()-]*(?:\*\*\d+)?(?: [-+] \d+)?"

_LEN: Final = re.compile(
    rf"^(?P<lo>{_BOUND}) <= len\((?P<p>\w+)\) <= (?P<hi>{_BOUND})$"
)
_ITEM_LEN: Final = re.compile(
    rf"^(?P<lo>{_BOUND}) <= len\((?P<p>\w+)\[i\]\) <= (?P<hi>{_BOUND})$"
)
_VALUES: Final = re.compile(
    rf"^(?P<lo>{_BOUND}) <= (?P<p>\w+)(?P<idx>(?:\[[ij]\])*) "
    rf"(?P<cmp><=|<) (?P<hi>{_BOUND})$"
)
_NODE_VALUE: Final = re.compile(
    rf"^(?P<lo>{_BOUND}) <= node\.value <= (?P<hi>{_BOUND})$"
)
_NODES: Final = re.compile(
    rf"^The (?:tree|list|graph) has between (?P<lo>{_BOUND}) and (?P<hi>{_BOUND}) "
    r"nodes(?P<tail>.*)$"
)
_TAIL_AND: Final = re.compile(
    r"^(?P<head>.+?),? and (?P<tail>(?:no|all|the|every|so|it|they|values|a |an ).+)$"
)


@dataclass
class Report:
    flags: list[str] = field(default_factory=list)
    unchecked: list[str] = field(default_factory=list)
    checked: int = 0


def _ok(text: str) -> Bound | None:
    try:
        return Bound.parse(text)
    except InvalidValueError:
        return None


def _range(lo: str, hi: str) -> Range | None:
    low, high = _ok(lo), _ok(hi)
    if low is None or high is None or low.value > high.value:
        return None
    return Range(low=low, high=high)


# --- the stub ----------------------------------------------------------------


def _raises_not_implemented(function: ast.FunctionDef) -> bool:
    return any(
        isinstance(node, ast.Raise) and "NotImplementedError" in ast.unparse(node)
        for node in ast.walk(function)
    )


@dataclass
class Parsed:
    summary: str
    details: str | None
    args: dict[str, str]
    returns: str | None
    raises: list[tuple[str, str]]
    problems: list[str]


_SECTIONS: Final = ("Args:", "Returns:", "Raises:")


def parse_docstring(doc: str | None) -> Parsed:
    problems: list[str] = []
    if not doc:
        return Parsed("", None, {}, None, [], ["no docstring"])
    lines = inspect.cleandoc(doc).splitlines()
    starts = [i for i, line in enumerate(lines) if line in _SECTIONS]
    head = lines[: starts[0]] if starts else lines
    paragraphs = [p for p in "\n".join(head).strip().split("\n\n") if p.strip()]
    summary = " ".join(paragraphs[0].split()) if paragraphs else ""
    details = "\n\n".join(paragraphs[1:]) if len(paragraphs) > 1 else None
    args: dict[str, str] = {}
    returns: str | None = None
    raises: list[tuple[str, str]] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        body = lines[start + 1 : end]
        while body and not body[-1].strip():
            body.pop()
        if any(not line.strip() for line in body):
            problems.append(f"blank line inside {lines[start]}")
        if lines[start] == "Returns:":
            returns = " ".join(" ".join(body).split())
            continue
        entries: list[list[str]] = []
        for line in body:
            match = re.match(r"^    (\w+): (.*)$", line)
            if match:
                entries.append([match.group(1), match.group(2)])
            elif entries and line.startswith("        "):
                entries[-1][1] += " " + line.strip()
            else:
                problems.append(f"unreadable line in {lines[start]}: {line!r}")
        for name, text in entries:
            text = " ".join(text.split())
            if lines[start] == "Args:":
                args[name] = text
            else:
                raises.append((name, text))
    return Parsed(summary, details, args, returns, raises, problems)


@dataclass
class Draft:
    function: Function
    owner: str | None


def _annotation(node: ast.expr | None) -> str | None:
    return ast.unparse(node) if node is not None else None


def draft_function(
    function: ast.FunctionDef, report: Report, where: str
) -> Function | None:
    parsed = parse_docstring(ast.get_docstring(function, clean=False))
    for problem in parsed.problems:
        report.flags.append(f"{where}: {problem}")
    parameters: list[Parameter] = []
    declared = [a for a in function.args.args if a.arg != "self"]
    for argument in declared:
        text = parsed.args.get(argument.arg)
        kind = _annotation(argument.annotation)
        if kind is None:
            report.flags.append(f"{where}: {argument.arg} has no annotation")
            return None
        if text is None:
            report.flags.append(f"{where}: no Args entry for {argument.arg}")
            text = "TODO"
        parameters.append(Parameter(name=argument.arg, type=kind, description=text))
    for name in parsed.args:
        if name not in [a.arg for a in declared]:
            report.flags.append(f"{where}: Args names {name}, which is not a parameter")
    returns: Returns | None = None
    kind = _annotation(function.returns)
    if function.name != "__init__":
        if kind is None:
            report.flags.append(f"{where}: no return annotation")
            return None
        text = parsed.returns
        if text is None and kind != "None":
            report.flags.append(f"{where}: no Returns entry")
            text = "TODO"
        returns = Returns(type=kind, description=text)
    return Function(
        name=function.name,
        summary=parsed.summary or "TODO",
        parameters=tuple(parameters),
        returns=returns,
        details=parsed.details,
        raises=tuple(Raises(type=t, description=d) for t, d in parsed.raises),
    )


def draft_signature(stub: str, report: Report, where: str) -> Signature | None:
    tree = ast.parse(stub)
    functions: list[Function] = []
    classes: list[ClassSignature] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and _raises_not_implemented(node):
            drafted = draft_function(node, report, f"{where}:{node.name}")
            if drafted is not None:
                functions.append(drafted)
        elif isinstance(node, ast.ClassDef):
            todo = [
                m
                for m in node.body
                if isinstance(m, ast.FunctionDef) and _raises_not_implemented(m)
            ]
            if not todo:
                continue
            methods = []
            for method in todo:
                drafted = draft_function(
                    method, report, f"{where}:{node.name}.{method.name}"
                )
                if drafted is not None:
                    methods.append(drafted)
            doc = parse_docstring(ast.get_docstring(node, clean=False))
            if doc.details or doc.args or doc.returns:
                report.flags.append(
                    f"{where}: class {node.name} docstring has more than a summary"
                )
            classes.append(
                ClassSignature(
                    name=node.name,
                    summary=doc.summary or "TODO",
                    methods=tuple(methods),
                )
            )
    if not functions and not classes:
        report.flags.append(f"{where}: nothing in the stub raises NotImplementedError")
        return None
    return Signature(functions=tuple(functions), classes=tuple(classes))


# --- the constraints ----------------------------------------------------------


def _all_parameters(signature: Signature) -> dict[str, list[Parameter]]:
    found: dict[str, list[Parameter]] = {}
    for _, function in signature.callables():
        for parameter in function.parameters:
            found.setdefault(parameter.name, []).append(parameter)
    return found


def _apply_function(
    function: Function, name: str, measure: str, value: Range
) -> Function:
    changes: dict[str, Range] = {measure: value}
    return replace(
        function,
        parameters=tuple(
            replace(p, **changes) if p.name == name else p  # type: ignore[arg-type]
            for p in function.parameters
        ),
    )


def _with(signature: Signature, name: str, measure: str, value: Range) -> Signature:
    return replace(
        signature,
        functions=tuple(
            _apply_function(f, name, measure, value) for f in signature.functions
        ),
        classes=tuple(
            replace(
                c,
                methods=tuple(
                    _apply_function(m, name, measure, value) for m in c.methods
                ),
            )
            for c in signature.classes
        ),
    )


def _node_parameters(signature: Signature, *, single: bool = True) -> list[str]:
    """Parameters that are linked structures; with `single=False`, containers too."""
    return sorted(
        {
            parameter.name
            for _, function in signature.callables()
            for parameter in function.parameters
            if (parameter.is_node if single else parameter.holds_nodes)
        }
    )


def _already(signature: Signature, name: str, measure: str) -> bool:
    return any(
        getattr(parameter, measure) is not None
        for parameter in _all_parameters(signature).get(name, [])
    )


_GRID: Final = re.compile(
    r"^(?:0 <= (?:rows|m) <= (?P<r>\d+) and "
    r"(?P<cmin>[01]) <= (?:columns|n) <= (?P<c>\d+)"
    r"(?:, for m rows of n \w+ each)?"
    r"|The grid has at most (?P<r2>\d+) rows and (?P<c2>\d+) columns, "
    r"and may be empty)$"
)
_PAIR: Final = re.compile(
    rf"^Each (?P<what>interval|meeting)(?:, the new one included,)? is \(start, end\) "
    rf"with (?P<lo>{_BOUND}) <= start (?P<cmp><=|<) end <= (?P<hi>{_BOUND})$"
)


def _is_pair(parameter: Parameter) -> bool:
    return "tuple[int, int]" in parameter.type


def _map_exact(
    signature: Signature, stripped: str
) -> tuple[Signature, list[str]] | None:
    """One constraint string that says one thing, or `None`."""
    parameters = _all_parameters(signature)
    nodes = _node_parameters(signature)
    grids = sorted({p.name for ps in parameters.values() for p in ps if p.depth == 2})

    for pattern, measure in ((_LEN, "length"), (_ITEM_LEN, "item_length")):
        match = pattern.match(stripped)
        if match and match.group("p") in parameters:
            name = match.group("p")
            value = _range(match.group("lo"), match.group("hi"))
            if value is None or _already(signature, name, measure):
                return None
            return _with(signature, name, measure, value), []
    match = _VALUES.match(stripped)
    if match and match.group("p") in parameters:
        name = match.group("p")
        high = match.group("hi")
        if match.group("cmp") == "<":
            high = f"{high} - 1"
        value = _range(match.group("lo"), high)
        if value is None or _already(signature, name, "values"):
            return None
        if match.group("idx").count("[") != parameters[name][0].depth:
            return None
        return _with(signature, name, "values", value), []
    match = _NODE_VALUE.match(stripped)
    holders = _node_parameters(signature, single=False)
    if match and holders:
        value = _range(match.group("lo"), match.group("hi"))
        if value is None or any(_already(signature, n, "values") for n in holders):
            return None
        for name in holders:
            signature = _with(signature, name, "values", value)
        return signature, []
    match = _NODES.match(stripped)
    if match and nodes and not match.group("tail").strip().startswith("and the"):
        value = _range(match.group("lo"), match.group("hi"))
        if value is None or any(_already(signature, n, "nodes") for n in nodes):
            return None
        for name in nodes:
            signature = _with(signature, name, "nodes", value)
        extra = match.group("tail").strip(" ,;")
        return signature, ([extra[0].upper() + extra[1:] + "."] if extra else [])
    match = _GRID.match(stripped)
    if match and len(grids) == 1 and not _already(signature, grids[0], "length"):
        rows = match.group("r") or match.group("r2")
        columns = match.group("c") or match.group("c2")
        low = match.group("cmin") or "0"
        length = _range("0", rows)
        width = _range(low, columns)
        if length is None or width is None:
            return None
        signature = _with(signature, grids[0], "length", length)
        return _with(signature, grids[0], "item_length", width), []
    match = _PAIR.match(stripped)
    if match:
        pairs = [n for n, ps in parameters.items() if any(_is_pair(p) for p in ps)]
        value = _range(match.group("lo"), match.group("hi"))
        if (
            value is None
            or not pairs
            or any(_already(signature, n, "values") for n in pairs)
        ):
            return None
        for name in pairs:
            signature = _with(signature, name, "values", value)
        order = "<" if match.group("cmp") == "<" else "<="
        what = match.group("what")
        return signature, [
            f"Each {what} is a pair (start, end) with start {order} end."
        ]
    return None


def map_constraint(
    signature: Signature, text: str
) -> tuple[Signature, list[str]] | None:
    """Fold one constraint string into the signature, or `None` if it will not go.

    Returns the new signature and any remainder that should stay a note. A
    string is tried whole first; only if that fails is a trailing ", and ..."
    split off, and only when what is left then maps -- so the splitter can never
    break up a sentence that was a note to begin with.
    """
    stripped = text.strip().rstrip(".")
    whole = _map_exact(signature, stripped)
    if whole is not None:
        return whole
    tail = _TAIL_AND.match(stripped)
    if tail is not None:
        head = _map_exact(signature, tail.group("head"))
        if head is not None:
            sentence = tail.group("tail").strip()
            return head[0], [*head[1], sentence[0].upper() + sentence[1:] + "."]
    if " and " in stripped and stripped.count("<=") >= 4:
        current = signature
        remainder: list[str] = []
        for half in stripped.split(" and "):
            mapped = _map_exact(current, half)
            if mapped is None:
                return None
            current, extra = mapped
            remainder.extend(extra)
        return current, remainder
    return None


# --- emitting ------------------------------------------------------------------

_PLAIN: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_\[\], |.]*$")


def _scalar(text: str, indent: int) -> str:
    """A YAML scalar for `text`, as a plain, quoted or folded one by length."""
    if "\n" in text:
        pad = " " * (indent + 2)
        body = "\n".join(pad + line if line else "" for line in text.splitlines())
        return "|-\n" + body
    if _PLAIN.match(text) and len(text) <= 72:
        return text
    if len(text) <= 72:
        return json.dumps(text, ensure_ascii=False)
    pad = " " * (indent + 2)
    wrapped = textwrap.wrap(
        text, width=88 - len(pad), break_long_words=False, break_on_hyphens=False
    )
    return ">-\n" + "\n".join(pad + line for line in wrapped)


def _bound(range_: Range) -> str:
    parts = []
    if range_.low is not None:
        parts.append(f"min: {range_.low.text}")
    if range_.high is not None:
        parts.append(f"max: {range_.high.text}")
    return "{" + ", ".join(parts) + "}"


def _emit_function(function: Function, indent: int) -> list[str]:
    pad = " " * indent
    out = [f"{pad}- name: {function.name}"]
    inner = pad + "  "
    out.append(f"{inner}summary: {_scalar(function.summary, indent + 2)}")
    if function.details:
        out.append(f"{inner}details: {_scalar(function.details, indent + 2)}")
    if function.parameters:
        out.append(f"{inner}parameters:")
        for parameter in function.parameters:
            out.append(f"{inner}  - name: {parameter.name}")
            deep = inner + "    "
            out.append(f"{deep}type: {_scalar(parameter.type, indent + 6)}")
            out.append(
                f"{deep}description: {_scalar(parameter.description, indent + 6)}"
            )
            for measure in ("length", "item_length", "values", "nodes"):
                value = getattr(parameter, measure)
                if value is not None:
                    out.append(f"{deep}{measure}: {_bound(value)}")
    if function.returns is not None:
        out.append(f"{inner}returns:")
        out.append(f"{inner}  type: {_scalar(function.returns.type, indent + 4)}")
        if function.returns.description is not None:
            out.append(
                f"{inner}  description: "
                f"{_scalar(function.returns.description, indent + 4)}"
            )
    if function.raises:
        out.append(f"{inner}raises:")
        for raised in function.raises:
            out.append(f"{inner}  - type: {raised.type}")
            out.append(
                f"{inner}    description: {_scalar(raised.description, indent + 6)}"
            )
    return out


def emit_yaml(signature: Signature) -> list[str]:
    out = ["  signature:"]
    if signature.functions:
        out.append("    functions:")
        for function in signature.functions:
            out.extend(_emit_function(function, 6))
    if signature.classes:
        out.append("    classes:")
        for cls in signature.classes:
            out.append(f"      - name: {cls.name}")
            out.append(f"        summary: {_scalar(cls.summary, 8)}")
            out.append("        methods:")
            for method in cls.methods:
                out.extend(_emit_function(method, 10))
    if signature.notes:
        out.append("  notes:")
        for note in signature.notes:
            out.append(f"    - {_scalar(note, 4)}")
    return out


def rewrite_stub(stub: str, signature: Signature) -> str:
    """The stub with every declared callable's docstring regenerated."""
    tree = ast.parse(stub)
    lines = stub.splitlines()
    edits: list[tuple[int, int, list[str]]] = []

    def docstring_edit(
        node: ast.FunctionDef | ast.ClassDef, text: str, indent: int
    ) -> None:
        first = node.body[0]
        assert isinstance(first, ast.Expr)
        edits.append(
            (
                first.lineno - 1,
                first.end_lineno or first.lineno,
                _emit_doc(text, indent),
            )
        )

    by_name = {f.name: f for f in signature.functions}
    classes = {c.name: c for c in signature.classes}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in by_name:
            function = by_name[node.name]
            docstring_edit(node, docstring_of(function.summary, function, indent=4), 4)
        elif isinstance(node, ast.ClassDef) and node.name in classes:
            cls = classes[node.name]
            docstring_edit(node, docstring_of(cls.summary, None, indent=4), 4)
            methods = {m.name: m for m in cls.methods}
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name in methods:
                    function = methods[method.name]
                    docstring_edit(
                        method, docstring_of(function.summary, function, indent=8), 8
                    )
    for start, end, replacement in sorted(edits, reverse=True):
        lines[start:end] = replacement
    return "\n".join(lines) + "\n"


def _emit_doc(text: str, indent: int) -> list[str]:
    pad = " " * indent
    body = text.splitlines()
    if len(body) == 1 and len(pad) + len(body[0]) + 6 <= 88:
        return [f'{pad}"""{body[0]}"""']
    out = [f'{pad}"""{body[0]}']
    out.extend(f"{pad}{line}" if line else "" for line in body[1:])
    out.append(f'{pad}"""')
    return out


# --- the walk -------------------------------------------------------------------


def _constraint_block(lines: list[str]) -> tuple[int, int, list[str]] | None:
    """Where `  constraints:` sits in the file, its extent and its strings."""
    for index, line in enumerate(lines):
        if line == "  constraints:":
            end = index + 1
            while end < len(lines) and (
                lines[end].startswith("    ") or not lines[end].strip()
            ):
                end += 1
            while end > index + 1 and not lines[end - 1].strip():
                end -= 1
            return index, end, lines[index + 1 : end]
    return None


def migrate(directory: Path, write: bool, report: Report) -> None:
    where = directory.name
    yaml_path = directory / "exercise.yaml"
    text = yaml_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    block = _constraint_block(lines)
    if block is None:
        report.flags.append(f"{where}: no constraints block")
        return
    start, end, raw = block
    loaded = yaml.safe_load(
        "constraints:\n"
        + "\n".join(line[2:] if line.startswith("  ") else line for line in raw)
    )
    strings = [str(c) for c in loaded.get("constraints", [])] if loaded else []
    stub_path = directory / "stub.py"
    stub = stub_path.read_text(encoding="utf-8")
    signature = draft_signature(stub, report, where)
    if signature is None:
        return
    notes: list[str] = []
    for string in strings:
        mapped = map_constraint(signature, string)
        if mapped is None:
            notes.append(string)
            continue
        signature, extra = mapped
        notes.extend(extra)
    signature = replace(signature, notes=tuple(notes))
    report.checked += sum(
        len(p.measures()) for _, f in signature.callables() for p in f.parameters
    )
    report.unchecked.extend(f"{where}: {note}" for note in notes)
    if "TODO" in "".join(emit_yaml(signature)):
        report.flags.append(f"{where}: has a TODO to write by hand")
    if write:
        new = lines[:start] + emit_yaml(signature) + lines[end:]
        yaml_path.write_text("\n".join(new) + "\n", encoding="utf-8", newline="\n")
        stub_path.write_text(
            rewrite_stub(stub, signature), encoding="utf-8", newline="\n"
        )


def regenerate_stubs(only: list[str]) -> int:
    """Rewrite each kata's stub docstrings from the signature in its YAML."""
    changed = 0
    for directory in sorted(content_root().glob("*/*/exercise.yaml")):
        directory = directory.parent
        if only and directory.name not in only:
            continue
        exercise = load_exercise(directory)
        if not isinstance(exercise.spec, KataSpec) or exercise.spec.signature is None:
            continue
        stub_path = directory / exercise.spec.stub
        before = stub_path.read_text(encoding="utf-8")
        after = rewrite_stub(before, exercise.spec.signature)
        if after != before:
            stub_path.write_text(after, encoding="utf-8", newline="\n")
            changed += 1
            print("rewrote", stub_path.relative_to(content_root()).as_posix())
    print(f"{changed} stubs rewritten")
    return 0


def main(argv: list[str]) -> int:
    if "--stubs" in argv:
        return regenerate_stubs([a for a in argv if not a.startswith("--")])
    write = "--write" in argv
    report = Report()
    root = content_root()
    directories = sorted(
        d.parent
        for d in root.glob("*/*/exercise.yaml")
        if "kind: kata" in d.read_text("utf-8")
    )
    for directory in directories:
        migrate(directory, write, report)
    print(f"{len(directories)} katas; {report.checked} bounds will be checked;")
    print(f"{len(report.unchecked)} constraints stay notes (printed, not enforced)")
    for flag in report.flags:
        print("FLAG", flag)
    if "--notes" in argv:
        for note in report.unchecked:
            print("NOTE", note)
    return 1 if report.flags else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
