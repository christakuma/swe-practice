"""Run a kata's examples against `solution.py`, and write what each one gave.

**This file is copied into the workspace and run by a different interpreter
invocation**, which is `report_plugin`'s situation exactly, and every
constraint it lists holds here too: it imports nothing from `practice`, the
interpreter runs in isolated mode so the workspace is put on `sys.path` by
hand, and it is read off disk rather than held as a string so the file linted
and typed in this project is the file the subprocess runs (ADR 0029).

**The evaluation is the content suite's, on purpose.** `tests/content/
test_katas.py` runs every example against the reference and compares `repr` of
the *plain* form (ADR 0027), and an example that the suite says the reference
passes has to read the same way when the solver's code passes it -- otherwise a
correct answer could show as a mismatch on a linked list compared by memory
address. So `_plain` and `_run` are the same rules, written again in a file
that cannot import the suite, and `tests/integration/kata/test_examples.py`
runs this harness against a shipped reference to hold the two together.

**The report is rewritten after every example**, not once at the end. A run is
killed at the kata's time limit, and an example that loops forever is exactly
the case a solver presses Run to find; writing as it goes means the examples
before the one that hung still come back with their results.

**The solver's code is untrusted and this is where it runs**, inside the
sandbox's process limits like the hidden suite. Nothing here is a containment:
an example's `print` is captured and capped, an exception becomes a line of
text, and anything worse ends the process and is reported by the runner from
the outside.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Final

HERE: Final = Path(__file__).resolve().parent

#: What the runner writes and what this writes back. Names, not arguments, so
#: the argv the runner builds carries no data at all.
EXAMPLES_FILE: Final = "practice_examples.json"
REPORT_FILE: Final = "practice_examples_report.json"

#: Bumped if the report's shape changes, so a stale copy is read as no report.
SCHEMA_VERSION: Final = 1

#: How far a linked structure is followed before it is called cyclic -- the
#: content suite's limit, for the content suite's reason.
WALK_LIMIT: Final = 10_000

#: How much of an example's printed output is kept. A `print` in a loop is a
#: normal way to debug and can produce megabytes; the first screenful is the
#: part anybody reads.
STDOUT_LIMIT: Final = 2_000


class _CyclicError(ValueError):
    """A returned list that does not end."""


def _plain(value: Any) -> object:  # noqa: ANN401  (the solver's own node classes)
    """Turn a returned node into data that can be compared and printed.

    Recognised by shape rather than by class, because every kata declares its
    own `ListNode` and `TreeNode` in its stub and defines no `__eq__` on them.
    The rule `tests/content/test_katas.py::_plain` states, with the walk limit
    raised as an error rather than asserted -- here it is the solver's list.
    """
    if isinstance(value, list | tuple):
        return type(value)(_plain(item) for item in value)
    if hasattr(value, "left") and hasattr(value, "right"):
        return ("tree", value.value, _plain(value.left), _plain(value.right))
    link = next((name for name in ("next", "next_node") if hasattr(value, name)), None)
    if link is None:
        return value
    values: list[object] = []
    node = value
    while node is not None:
        if len(values) >= WALK_LIMIT:
            raise _CyclicError("the returned list does not end")
        values.append(node.value)
        node = getattr(node, link)
    return ("list", *values)


def _run(source: str, namespace: dict[str, object]) -> object:
    """Execute an example's input in a copy of the module, and give its last line."""
    *setup, last = ast.parse(source).body
    if not isinstance(last, ast.Expr):
        raise TypeError("this example's input does not end in an expression")
    scope = dict(namespace)
    exec(compile(ast.Module(setup, type_ignores=[]), "<example>", "exec"), scope)  # noqa: S102
    return eval(compile(ast.Expression(last.value), "<example>", "eval"), scope)  # noqa: S307


def _last_line(error: BaseException) -> str:
    """The exception as its last traceback line: `IndexError: index out of range`."""
    return traceback.format_exception_only(error)[-1].strip()


def _write(report: dict[str, object]) -> None:
    (HERE / REPORT_FILE).write_text(json.dumps(report), encoding="utf-8")


def _example(
    example: dict[str, str], namespace: dict[str, object]
) -> dict[str, object]:
    """One example's row. Never raises for anything the solver's code does."""
    captured = io.StringIO()
    row: dict[str, object] = {"input": example["input"], "actual": None, "error": None}
    try:
        # Against the module alone, never against what the input left behind --
        # the content suite's rule, which keeps `output: numbers` unwritable.
        row["expected"] = repr(_plain(eval(example["output"], dict(namespace))))  # noqa: S307
    except Exception as error:  # a broken stub class, reported as such
        row["expected"] = example["output"].strip()
        row["error"] = f"could not build the expected value: {_last_line(error)}"
        return row
    try:
        with contextlib.redirect_stdout(captured):
            got = _run(example["input"], namespace)
        row["actual"] = repr(_plain(got))
    # `BaseException`, so a solver's `exit()` or a `RecursionError` is a row
    # rather than the end of the run. `KeyboardInterrupt` is the one exception:
    # it is the runner stopping this process, not the solver's code failing.
    except KeyboardInterrupt:
        raise
    except BaseException as error:
        row["error"] = _last_line(error)
    row["stdout"] = captured.getvalue()[:STDOUT_LIMIT]
    return row


def main() -> None:
    sys.path.insert(0, str(HERE))
    examples = json.loads((HERE / EXAMPLES_FILE).read_text(encoding="utf-8"))
    report: dict[str, object] = {
        "version": SCHEMA_VERSION,
        "problem": None,
        "examples": [],
    }
    try:
        # The solver's file, importable only now, and never by this project.
        import solution  # type: ignore[import-not-found]  # noqa: PLC0415
    except KeyboardInterrupt:
        raise
    except BaseException as error:
        report["problem"] = f"your solution could not be imported: {_last_line(error)}"
        _write(report)
        return

    namespace = dict(vars(solution))
    rows: list[dict[str, object]] = []
    report["examples"] = rows
    for example in examples:
        rows.append(_example(example, namespace))
        _write(report)
    _write(report)


if __name__ == "__main__":
    main()
