"""A kata's declared bounds, enforced from inside the reference solution.

Phase 28's answer to ADR 0022's finding that a constraint nothing checks is a
comment. A kata declares ranges for what its tests pass in
(`domain/signature.py`); this module makes the reference solution refuse an
argument outside them, so a hidden suite that steps out of its own stated bounds
fails the build the moment `test_katas.py` grades the reference.

**Appended to the reference, not imported by it.** The graded process runs
`python -I` in a workspace with only `solution.py` on its path, and the hidden
suite does `from solution import f`, so the only way to sit between the suite
and the function is to be in the same file. `bounded_source` returns the
reference followed by this module's own text and an `install` call; the file
is therefore valid Python on its own (a test imports it for the checker) *and*
the footer (the content suite appends it). That dual use is why it avoids
`from __future__` -- it has to be legal after other code -- and imports only the
standard library.

**Three rules the checker keeps, each found by a case that broke the first
version:**

* **Only the outermost call is checked.** A recursive reference passes its own
  sub-problems back through the wrapped name, and a helper argument is not a
  promise about the suite's inputs. A depth counter lets the first call through
  the check and every nested one past it.
* **It reads arguments the way the data says, not the way a test double says.**
  `Tripwire` and `Watched` are `list` subclasses whose `__iter__` and
  `__getitem__` raise or count, because that is how a suite proves an early
  return. The checker walks them with `list.__iter__` and `list.__len__`, which
  no override can see, so it neither trips them nor charges the solver for its
  own looking.
* **A node is followed by the four link names katas use.** `left`, `right`,
  `next` and `neighbours`, with a visited set so a cyclic list or an undirected
  graph ends. `NODE_LINKS` in `domain/signature.py` is the same list and a test
  holds the two together.
"""

import functools
import inspect
import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

_NODE_LINKS = ("left", "right", "next", "neighbours")
_SEQUENCES: tuple[type, ...] = (list, tuple, set, frozenset)

#: Re-entrancy depth, shared by every wrapped callable.
_depth = [0]

#: The last argument each parameter was checked on, as `(object, length)`.
#:
#: A search function is called thousands of times on one two-million-element
#: list, and a probe that scans the list per call turns an O(log n) answer into
#: an O(n) one -- two suites hit their time limit before this existed. The same
#: object is looked at once -- held by reference, not by `id()`, because a freed
#: list's address is reused by the next literal of the same length. Mutating
#: it between calls into a violation would slip past, which no hidden suite
#: does, and the failure it risks is a bound missed, never one invented.
#: Holding it keeps one argument per parameter alive, and only for one
#: suite: the footer lives in the graded subprocess, not the pytest worker.
_looked_at: dict[tuple[str, str], tuple[object, int | None]] = {}


def _length(value: object) -> int | None:  # noqa: PLR0911
    """`len(value)` through the builtin, so a subclass's `__len__` is not asked."""
    if isinstance(value, list):
        return list.__len__(value)
    if isinstance(value, tuple):
        return tuple.__len__(value)
    if isinstance(value, str):
        return str.__len__(value)
    if isinstance(value, dict):
        return dict.__len__(value)
    if isinstance(value, set):
        return set.__len__(value)
    if isinstance(value, frozenset):
        return frozenset.__len__(value)
    return None


def _elements(value: object) -> list[Any]:
    """The elements of a builtin sequence, bypassing any overridden iteration."""
    if isinstance(value, list):
        return list(list.__iter__(value))
    if isinstance(value, tuple):
        return list(tuple.__iter__(value))
    if isinstance(value, set):
        return list(set.__iter__(value))
    if isinstance(value, frozenset):
        return list(frozenset.__iter__(value))
    return []


def _iterate(value: object) -> Iterator[Any]:
    """The elements of a builtin sequence, lazily and through the base class.

    `_elements` copies, which is right for the handful of roots a container of
    nodes holds and wrong for a million integers: the suites that measure a
    solution's allocations (`uses-constant-extra-space`) run *inside* the
    measured window, and a probe that copies its argument is charged to the
    solver. This allocates one iterator.
    """
    if isinstance(value, list):
        return list.__iter__(value)
    if isinstance(value, tuple):
        return tuple.__iter__(value)
    if isinstance(value, set):
        return set.__iter__(value)
    if isinstance(value, frozenset):
        return frozenset.__iter__(value)
    return iter(())


def _integers(value: object) -> Iterator[int]:
    """Every integer inside `value`, however deeply nested in lists and tuples."""
    if isinstance(value, int) and not isinstance(value, bool):
        yield value
        return
    stack = [_iterate(value)]
    while stack:
        for current in stack[-1]:
            if isinstance(current, bool):
                continue
            if isinstance(current, int):
                yield current
            elif isinstance(current, _SEQUENCES):
                stack.append(_iterate(current))
                break
        else:
            stack.pop()


def _reachable(roots: list[Any]) -> list[Any]:
    """Every node reachable from `roots` along `_NODE_LINKS`, each once."""
    seen: set[int] = set()
    found: list[Any] = []
    stack = list(roots)
    while stack:
        node = stack.pop()
        if node is None or id(node) in seen or isinstance(node, str | int | float):
            continue
        seen.add(id(node))
        found.append(node)
        for name in _NODE_LINKS:
            target = getattr(node, name, None)
            if isinstance(target, _SEQUENCES):
                stack.extend(_elements(target))
            elif target is not None:
                stack.append(target)
    return found


def _outside(number: int, bounds: list[int | None]) -> bool:
    low, high = bounds
    return (low is not None and number < low) or (high is not None and number > high)


def _say(bounds: list[int | None]) -> str:
    low, high = bounds
    return f"{'-inf' if low is None else low}..{'inf' if high is None else high}"


def _extremes(numbers: Iterator[int]) -> tuple[int, int] | None:
    """The smallest and the largest, or `None` for none at all."""
    low: int | None = None
    high: int | None = None
    for number in numbers:
        if low is None or number < low:
            low = number
        if high is None or number > high:
            high = number
    return None if low is None or high is None else (low, high)


def _integer_extremes(value: object) -> tuple[int, int] | None:
    """`_extremes(_integers(value))`, at the speed of C when it can be.

    `min` and `max` over a list's own iterator are two passes in C with nothing
    allocated, against a Python loop per element; for a million integers that
    is the difference between a few milliseconds and a time limit. They fail
    with a `TypeError` the moment an element is a list or a string, and then the
    general walk takes over.
    """
    if isinstance(value, list | tuple):
        try:
            return int(min(_iterate(value))), int(max(_iterate(value)))
        except (TypeError, ValueError):
            pass
    return _extremes(_integers(value))


def _worst(extremes: tuple[int, int] | None, bounds: list[int | None]) -> int | None:
    """The extreme furthest outside `bounds`, or `None` if both are inside.

    The furthest rather than the first, because the first offender is an
    accident of iteration order and an author widening a bound wants the size of
    the gap, not a sample of it.
    """
    if extremes is None:
        return None
    low, high = bounds
    smallest, largest = extremes
    below = low - smallest if low is not None and smallest < low else 0
    above = largest - high if high is not None and largest > high else 0
    if below == above == 0:
        return None
    return smallest if below > above else largest


def _size_problems(label: str, value: object, spec: dict[str, Any]) -> list[str]:
    found: list[str] = []
    if "length" in spec:
        size = _length(value)
        if size is not None and _outside(size, spec["length"]):
            found.append(f"{label}: length {size} is outside {_say(spec['length'])}")
    if "item_length" in spec:
        sizes = (
            size
            for size in (_length(item) for item in _iterate(value))
            if size is not None
        )
        worst = _worst(_extremes(sizes), spec["item_length"])
        if worst is not None:
            found.append(
                f"{label}: an element has length {worst}, outside "
                f"{_say(spec['item_length'])}"
            )
    return found


def _node_problems(label: str, value: object, spec: dict[str, Any]) -> list[str]:
    found: list[str] = []
    roots = _elements(value) if _length(value) is not None else [value]
    nodes = _reachable(roots)
    if "nodes" in spec and _outside(len(nodes), spec["nodes"]):
        found.append(f"{label}: {len(nodes)} nodes is outside {_say(spec['nodes'])}")
    if "values" in spec:
        numbers = (
            number
            for number in (getattr(node, "value", None) for node in nodes)
            if isinstance(number, int) and not isinstance(number, bool)
        )
        worst = _worst(_extremes(numbers), spec["values"])
        if worst is not None:
            found.append(
                f"{label}: node.value {worst} is outside {_say(spec['values'])}"
            )
    return found


def _value_problems(label: str, value: object, spec: dict[str, Any]) -> list[str]:
    worst = _worst(_integer_extremes(value), spec["values"])
    if worst is None:
        return []
    return [f"{label}: value {worst} is outside {_say(spec['values'])}"]


def problems(label: str, value: object, spec: dict[str, Any]) -> list[str]:
    """Every way `value` steps outside what `spec` declares for it."""
    if type(value) is int:
        # The common argument of a method called 10**5 times, and all it can
        # break is its value: no walk, no list, nothing built.
        if "values" in spec and _outside(value, spec["values"]):
            return [f"{label}: value {value} is outside {_say(spec['values'])}"]
        return []
    found = _size_problems(label, value, spec)
    if spec.get("holds_nodes", False):
        found += _node_problems(label, value, spec)
    elif "values" in spec:
        found += _value_problems(label, value, spec)
    return found


def _guard(
    function: Callable[..., Any],
    label: str,
    params: dict[str, Any],
    rebind: Callable[[Callable[..., Any]], None] | None,
) -> Callable[..., Any]:
    """`function` wrapped in its check, and out of the way of its own recursion.

    `rebind` puts a callable back where a module-level function lives. While
    the outermost call runs, the *raw* function is what its name points at, so a
    recursive reference calls itself with no wrapper frame in between. The first
    version did not do this and it was wrong in a way only a deep tree could
    show: a wrapper doubles the frames per level of recursion, and
    `inverts-a-deep-tree` ran out of stack at half the depth its author had
    measured the reference to survive. The check must not change how much stack
    the answer has.

    **Methods are not rebound**, because assigning to a class attribute throws
    away the interpreter's attribute cache for the whole class, and a
    `median-of-a-stream` that is called 2 * 10**5 times paid five seconds for it.
    A method that recurses through `self` pays the doubled frames instead, and no
    kata's does.

    Arguments are found by position or keyword from a precomputed table rather
    than through `inspect.signature(...).bind`, which was the other half of that
    five seconds.
    """
    names = list(inspect.signature(function).parameters)
    checks = [(names.index(name), name, spec) for name, spec in params.items()]

    @functools.wraps(function)
    def checked(*args: Any, **kwargs: Any) -> Any:
        if _depth[0]:
            return function(*args, **kwargs)
        _depth[0] += 1
        try:
            found: list[str] = []
            for index, name, spec in checks:
                if name in kwargs:
                    argument = kwargs[name]
                elif index < len(args):
                    argument = args[index]
                else:
                    continue
                length = _length(argument)
                seen = _looked_at.get((label, name))
                if seen is not None and seen[0] is argument and seen[1] == length:
                    continue
                found += problems(f"{label}({name})", argument, spec)
                if not found:
                    _looked_at[(label, name)] = (argument, length)
            if found:
                raise AssertionError("DECLARED BOUND BROKEN: " + "; ".join(found))
            if rebind is None:
                return function(*args, **kwargs)
            rebind(function)
            try:
                return function(*args, **kwargs)
            finally:
                rebind(checked)
        finally:
            _depth[0] -= 1

    return checked


def install(namespace: dict[str, Any], spec: dict[str, Any]) -> None:
    """Wrap every declared callable in `namespace` with its bounds check."""
    for name, params in spec.get("functions", {}).items():

        def set_function(target: Callable[..., Any], key: str = name) -> None:
            namespace[key] = target

        namespace[name] = _guard(namespace[name], name, params, set_function)
    for class_name, methods in spec.get("classes", {}).items():
        cls = namespace[class_name]
        for method, params in methods.items():
            wrapped = _guard(
                getattr(cls, method), f"{class_name}.{method}", params, None
            )
            setattr(cls, method, wrapped)


# --- the test side: nothing below this line runs in the graded process ------

_MARK = "# --- the test side"


def probe_spec(signature: Any) -> dict[str, Any]:
    """The `install` argument for a `domain.signature.Signature`."""

    def parameters(function: Any) -> dict[str, Any]:
        found: dict[str, Any] = {}
        for parameter in function.parameters:
            entry: dict[str, Any] = {}
            for measure in ("length", "item_length", "values", "nodes"):
                range_ = getattr(parameter, measure)
                if range_ is not None:
                    low = range_.low.value if range_.low is not None else None
                    high = range_.high.value if range_.high is not None else None
                    entry[measure] = [low, high]
            if entry:
                entry["holds_nodes"] = parameter.holds_nodes
                found[parameter.name] = entry
        return found

    return {
        "functions": {f.name: parameters(f) for f in signature.functions},
        "classes": {
            c.name: {m.name: parameters(m) for m in c.methods}
            for c in signature.classes
        },
    }


def bounded_source(reference: str, signature: Any) -> str:
    """The reference followed by a footer that arms the checker.

    The checker is not pasted in as code: it is `exec`'d into a namespace of
    its own, so a reference that happens to define `_reachable` or `problems`
    (graph katas do) can neither shadow the checker nor be shadowed by it. The
    footer adds exactly one name to the module, and deletes it.
    """
    text = Path(__file__).read_text(encoding="utf-8")
    probe = text[: text.index(_MARK)]
    spec = json.dumps(probe_spec(signature))
    footer = (
        "_practice_probe = {}\n"
        f"exec(compile({probe!r}, '<bounds probe>', 'exec'), _practice_probe)\n"
        "_practice_probe['install'](\n"
        f"    globals(), _practice_probe['json'].loads({spec!r})\n"
        ")\n"
        "del _practice_probe\n"
    )
    return reference.rstrip("\n") + "\n\n\n" + footer
