"""Every kata on disk, actually solved — and actually failed.

The half of PLAN.md §9's content suite that Phase 4 lands: *"katas:
`solution.py` **passes** and `stub.py` **fails** (a test suite that passes an
empty stub is a broken test suite)"*. Both halves matter and the second is the
one people leave out. A suite that passes the stub is not a weak suite, it is a
suite that grades nothing, and it would make its exercise report success for
every solution ever submitted to it.

Parametrized over the real `content/` directory, so adding a kata adds test
cases without touching this file — the content-as-data bet applied to its own
tests. It is the slowest file in the project per exercise: two pytest
subprocesses per kata. That is the price of proving content works, and §11 is
explicit that structural validation is not the same claim.

**What this cannot prove, and does not pretend to.** That the suite is
*discriminating* — that it would reject a plausible wrong answer rather than
only an unimplemented one. `tests/integration/kata/test_pytest_runner.py` holds
one such case for two-sum by hand; the general form would need a counter-example
per kata, which is what git scenarios already require (§5.4) and what katas
should grow if the library gets large enough to need it.

**The examples a kata shows are run here too** (ADR 0027), and that half costs
nothing: each one is a few lines executed in-process against the reference, so
it adds milliseconds to a file whose every other test starts a subprocess.
In-process is right for it and wrong for grading. Grading runs a *solver's*
source, which is untrusted and goes through the sandbox; an example runs the
*author's* reference, which is trusted content in the same sense a fixture is
(§8.1), and what is being checked is the page rather than the solution.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any

import pytest

from practice.adapters.content import ContentError, load_exercise
from practice.adapters.content.validation import discover
from practice.adapters.kata import KataGrader, PytestKataRunner
from practice.adapters.sandbox import SubprocessSandboxProvisioner, find_git
from practice.config import content_root
from practice.domain.attempt import Attempt, AttemptPolicy, ComplexityClaim
from practice.domain.exercise import KataSpec
from practice.domain.ids import AttemptId
from practice.domain.signature import docstring_of
from practice.domain.verdict import Outcome
from tests.content.bounds_probe import bounded_source
from tests.fakes import FakeClock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from practice.adapters.sandbox import SubprocessWorkspace
    from practice.domain.exercise import Example, Exercise
    from practice.domain.signature import Function
    from practice.domain.verdict import Verdict

CONTENT_ROOT = content_root()


def _identify(directory: Path) -> str:
    return directory.relative_to(CONTENT_ROOT).as_posix()


def _kata_directories() -> list[Path]:
    """Every kata directory, found defensively.

    A directory that will not load belongs to no kind and is reported by the
    `validate` suite instead, rather than crashing collection here.
    """
    found = []
    for directory in sorted(discover(CONTENT_ROOT)):
        try:
            exercise = load_exercise(directory)
        except ContentError:
            continue
        if isinstance(exercise.spec, KataSpec) and not exercise.is_variant:
            found.append(directory)
    return found


#: The standard katas. Their variants are graded by `test_variants.py`, from
#: these same tests and fixtures -- a second *file*, because `--dist loadfile`
#: puts a file on one worker and this one is already the suite's critical path
#: (CLAUDE.md). Doubling it would have moved the floor of every run; a sibling
#: runs beside it.
KATA_DIRECTORIES = _kata_directories()

type Grade = Callable[[str, ComplexityClaim | None], Verdict]


@pytest.fixture(scope="session")
def git() -> Path:
    """Resolve git once, failing loudly rather than skipping.

    A content suite that silently skips when a tool is missing reports success
    exactly as loudly as one that ran every kata (PLAN.md §9).
    """
    return find_git()


@pytest.fixture(params=KATA_DIRECTORIES, ids=_identify)
def kata_directory(request: pytest.FixtureRequest) -> Path:
    directory: Path = request.param
    return directory


@pytest.fixture
def exercise(kata_directory: Path) -> Exercise:
    return load_exercise(kata_directory)


@pytest.fixture
def spec(exercise: Exercise) -> KataSpec:
    assert isinstance(exercise.spec, KataSpec)
    return exercise.spec


@pytest.fixture
def grade(git: Path, tmp_path: Path, exercise: Exercise) -> Iterator[Grade]:
    """Grade a source against this kata, in a workspace of its own each time.

    A factory rather than one workspace, because grading writes `solution.py`
    and a report into it: a second grading in the same directory would start
    from the first one's leftovers, and what it proved would depend on the order
    the tests happen to be declared in.
    """
    del git  # requested so a missing tool fails here, not mid-fixture
    provisioner = SubprocessSandboxProvisioner(
        content_root=CONTENT_ROOT, workspace_root=tmp_path / "ws"
    )
    grader = KataGrader(PytestKataRunner())
    provisioned: list[SubprocessWorkspace] = []

    def run(source: str, claim: ComplexityClaim | None = None) -> Verdict:
        attempt_id = AttemptId.parse(
            f"{len(provisioned):08x}-0000-4000-8000-000000000000"
        )
        workspace = provisioner.provision(exercise, attempt_id)
        provisioned.append(workspace)

        clock = FakeClock()
        attempt = Attempt(
            attempt_id=attempt_id,
            exercise_id=exercise.id,
            policy=AttemptPolicy.for_exercise(exercise),
            started_at=clock.now(),
        )
        attempt.save_solution(source, at=clock.now())
        if claim is not None:
            attempt.declare_complexity(claim)
        return grader.grade(exercise, workspace, attempt)

    try:
        yield run
    finally:
        for workspace in provisioned:
            workspace.dispose()


def _read(directory: Path, name: str) -> str:
    return (directory / name).read_text(encoding="utf-8")


# --- the walk --------------------------------------------------------------


def test_there_are_katas_to_grade() -> None:
    """Without this, every parametrized test below is vacuously true."""
    assert KATA_DIRECTORIES


# --- every kata ------------------------------------------------------------


def test_its_reference_solution_passes_every_check(
    grade: Grade, spec: KataSpec, kata_directory: Path
) -> None:
    """The guarantee `practice validate` admitted it could not make until now.

    The complexity expectation, where there is one, is declared to match — so a
    failure here is about the solution and the suite rather than about an
    advisory the reference was never going to satisfy.

    **The reference runs with its declared bounds armed** (ADR 0035): every
    argument the hidden suite passes is checked against the ranges under
    `signature:`, and one outside them fails the check with a message naming the
    argument. It is this test and not a sibling because a sibling would grade
    the reference a second time, and a subprocess per kata is what makes this
    file the suite's critical path (CLAUDE.md). The wrapper only ever *raises*,
    so a pass here is a pass of the plain reference on in-range inputs;
    `test_bounds_probe.py` holds the proof that it can fail.
    """
    claim = (
        ComplexityClaim(
            time=spec.complexity.expected_time, space=spec.complexity.expected_space
        )
        if spec.complexity is not None
        else None
    )

    assert spec.signature is not None
    verdict = grade(
        bounded_source(_read(kata_directory, spec.reference), spec.signature), claim
    )

    assert verdict.outcome is Outcome.PASS, "\n".join(
        f"{report.check_id}: {report.actual} -- {report.explanation}"
        for report in verdict.reports
        if not report.passed
    )


#: Stub verdicts already computed, keyed by exercise id.
#:
#: Two tests read this verdict and a plain fixture graded it twice — a
#: provisioned workspace and a pytest subprocess each time, for an answer that
#: cannot differ. Memoised rather than made module-scoped because the `grade`
#: factory is built over a per-test workspace root and the autouse
#: `_own_database` fixture in `tests/conftest.py` is function-scoped; what is
#: cached is the `Verdict`, which is data.
_STUB_VERDICTS: dict[str, Verdict] = {}


@pytest.fixture
def stub_verdict(grade: Grade, spec: KataSpec, kata_directory: Path) -> Verdict:
    """The stub, graded once for every test that reads the result."""
    key = _identify(kata_directory)
    cached = _STUB_VERDICTS.get(key)
    if cached is None:
        cached = grade(_read(kata_directory, spec.stub), None)
        _STUB_VERDICTS[key] = cached
    return cached


def test_its_stub_fails(stub_verdict: Verdict) -> None:
    """A suite that passes an unimplemented stub grades nothing at all.

    Only that the verdict *fails* is asserted, not that every single check does:
    a stub that happens to satisfy a trivial case — an empty-input test, say — is
    a legitimate kata, while one that satisfies all of them is a broken one.
    """
    assert stub_verdict.outcome is Outcome.FAIL


def test_its_hidden_suite_holds_more_than_one_test(stub_verdict: Verdict) -> None:
    """One check is not a kata.

    Counted off the *stub* run rather than the reference, and that is deliberate
    rather than incidental: a check count taken from a passing run cannot
    distinguish a one-test suite from a one-test suite that passed, which is the
    thing being ruled out. The stub run is also the cheap one to count, since the
    complexity advisory is excluded by severity.
    """
    required = [report for report in stub_verdict.reports if report.is_required]

    assert len(required) > 1, [report.check_id for report in required]


def test_its_declared_complexity_is_compared_rather_than_graded(
    grade: Grade, spec: KataSpec, kata_directory: Path
) -> None:
    """A deliberately absurd claim must never fail the attempt.

    Static Big-O analysis of arbitrary code is not something this tool pretends
    to do (PLAN.md §7), so a disagreement is an advisory to reconcile.

    Both branches assert something, which is why there is no `pytest.skip` here:
    a kata that states an expectation gets exactly one advisory, and a kata that
    states none gets no complexity check at all — inventing one would fail every
    attempt at an exercise whose author was simply quieter.
    """
    verdict = grade(
        _read(kata_directory, spec.reference),
        ComplexityClaim(time="O(n!)", space="O(n!)"),
    )

    assert verdict.passed, "a complexity claim must never fail an attempt"
    if spec.complexity is None:
        assert verdict.outcome is Outcome.PASS
        assert verdict.advisories == ()
    else:
        assert verdict.outcome is Outcome.PASS_WITH_ADVISORIES
        assert len(verdict.advisories) == 1


# --- the statement: constraints and examples -------------------------------

#: How far a linked structure is followed before it is called cyclic. Far above
#: any example on the page and far below anything that would hang the suite.
_WALK_LIMIT = 10_000


def _plain(value: Any) -> object:
    """Turn a returned node into data that can be compared and printed.

    A kata's `ListNode` and `TreeNode` are the solver's own classes and define
    no `__eq__`, so two equal lists compare unequal and print as two memory
    addresses. Recognised by shape rather than by name or by import, because
    every kata declares its own copy of the class in its own stub -- there is
    no shared type to test against, deliberately (a kata is one file). That
    is also why the parameter is `Any`: the attributes read here belong to
    classes this module can never import.

    A tree keeps its `None` children, which is what makes a left-only child a
    different value from a right-only one. A list is walked with a limit, so an
    example whose answer accidentally loops fails here instead of hanging.
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
        assert len(values) < _WALK_LIMIT, "the list in this example does not end"
        values.append(node.value)
        node = getattr(node, link)
    return ("list", *values)


def _reference_namespace(directory: Path, spec: KataSpec) -> dict[str, object]:
    """The reference solution's globals: what a solver's file would define."""
    namespace: dict[str, object] = {"__name__": "solution"}
    code = compile(_read(directory, spec.reference), spec.reference, "exec")
    # Trusted content, executed on purpose: the reference is the author's own
    # answer, in this repository, and running it is the only way to learn what
    # it returns. A solver's source never comes near this function.
    exec(code, namespace)  # noqa: S102
    return namespace


def _run(example: Example, namespace: dict[str, object]) -> tuple[object, object]:
    """What the input's last line gives, and what the output says it should.

    Each half gets its own copy of the namespace. The output is evaluated
    against the module alone and never against what the input left behind, so
    `output: numbers` cannot be written -- an expectation that names the very
    list the input mutated is the hand-counted length ADR 0022 is about.
    """
    *setup, last = ast.parse(example.input).body
    assert isinstance(last, ast.Expr), (
        "an example's input must end in an expression, whose value is the output"
    )
    scope = dict(namespace)
    exec(compile(ast.Module(setup, type_ignores=[]), "<input>", "exec"), scope)  # noqa: S102
    got = eval(compile(ast.Expression(last.value), "<input>", "eval"), scope)  # noqa: S307
    want = eval(example.output, dict(namespace))  # noqa: S307
    return got, want


def test_it_states_its_constraints(spec: KataSpec) -> None:
    """A problem with no stated bounds leaves the algorithm to guesswork.

    "The list may be long" was how the first eighty-three prompts said it, and
    a solver cannot choose between `O(n log n)` and `O(n^2)` from an adjective.
    A quality rule rather than a domain invariant, so it is asserted here and
    the schema lets a draft load without one (`domain/exercise.py`).
    """
    assert spec.constraints


def test_it_shows_more_than_one_example(spec: KataSpec) -> None:
    """One example cannot tell a rule from a coincidence."""
    assert len(spec.examples) > 1


def _normal(annotation: str) -> str:
    """An annotation as `ast.unparse` spells it, so `list[int]` is `list[ int ]`."""
    return ast.unparse(ast.parse(annotation, mode="eval").body)


def _signature_problems(source: str, spec: KataSpec, *, annotated: bool) -> list[str]:
    """Every way `source` disagrees with the callables `spec.signature` declares.

    By AST rather than by importing, so a stub that raises on import and a
    reference with side effects are read the same way. Parameter *names and
    order* are always compared; annotations only where the file has them, and
    for the stub always, because the stub is what the solver is shown.
    """
    assert spec.signature is not None
    tree = ast.parse(source)
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    problems: list[str] = []

    def compare(node: ast.FunctionDef | None, declared: Function, where: str) -> None:
        if node is None:
            problems.append(f"{where} is declared and the file does not define it")
            return
        arguments = [a for a in node.args.args if a.arg != "self"]
        if [a.arg for a in arguments] != [p.name for p in declared.parameters]:
            took = ", ".join(a.arg for a in arguments)
            declares = ", ".join(p.name for p in declared.parameters)
            problems.append(
                f"{where} takes ({took}), the signature declares ({declares})"
            )
            return
        for argument, parameter in zip(arguments, declared.parameters, strict=True):
            if argument.annotation is None:
                if annotated:
                    problems.append(f"{where}: {parameter.name} has no annotation")
            elif ast.unparse(argument.annotation) != _normal(parameter.type):
                problems.append(
                    f"{where}: {parameter.name} is {ast.unparse(argument.annotation)}, "
                    f"declared {parameter.type}"
                )
        if declared.returns is None:
            return
        if node.returns is None:
            if annotated:
                problems.append(f"{where} has no return annotation")
        elif ast.unparse(node.returns) != _normal(declared.returns.type):
            problems.append(
                f"{where} returns {ast.unparse(node.returns)}, "
                f"declared {declared.returns.type}"
            )

    for function in spec.signature.functions:
        compare(functions.get(function.name), function, function.name)
    for cls in spec.signature.classes:
        found = classes.get(cls.name)
        if found is None:
            problems.append(
                f"class {cls.name} is declared and the file does not define it"
            )
            continue
        methods = {n.name: n for n in found.body if isinstance(n, ast.FunctionDef)}
        for method in cls.methods:
            compare(methods.get(method.name), method, f"{cls.name}.{method.name}")
    return problems


def test_its_stub_and_reference_agree_with_the_declared_signature(
    spec: KataSpec, kata_directory: Path
) -> None:
    """The names a solver is told to implement are the ones the page declares.

    Three places say what a kata's callable takes: the `signature:` block, the
    stub and the reference. Before Phase 28 nothing tied them together, and the
    page's description could drift from the code a solver was handed without any
    test noticing. The stub must match annotation for annotation; the
    reference only has to take the same arguments, in the same order, because
    a reference is allowed to be less decorated than the file it answers.
    """
    stub = _signature_problems(_read(kata_directory, spec.stub), spec, annotated=True)
    reference = _signature_problems(
        _read(kata_directory, spec.reference), spec, annotated=False
    )

    assert stub == [], f"stub.py: {stub}"
    assert reference == [], f"solution.py: {reference}"


def _expected_docstrings(spec: KataSpec) -> dict[str, str]:
    """Every generated docstring, keyed by where it sits in the stub."""
    assert spec.signature is not None
    expected = {
        function.name: docstring_of(function.summary, function, indent=4)
        for function in spec.signature.functions
    }
    for cls in spec.signature.classes:
        expected[cls.name] = docstring_of(cls.summary, None, indent=4)
        for method in cls.methods:
            expected[f"{cls.name}.{method.name}"] = docstring_of(
                method.summary, method, indent=8
            )
    return expected


def test_its_stub_docstrings_are_generated_from_the_signature(
    spec: KataSpec, kata_directory: Path
) -> None:
    """The docstring is derived, so it cannot be typed beside the fields.

    The first 245 stubs each described their arguments twice -- once in the
    docstring and once in a prose prompt -- and the two were free to disagree.
    The docstring is now `docstring_of(...)` over the declared fields and this
    compares them verbatim, so editing one without the other fails here, with
    the text the stub should hold in the message. `tools/migrate_katas.py
    --stubs` rewrites them.
    """
    tree = ast.parse(_read(kata_directory, spec.stub))
    found: dict[str, str | None] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            found[node.name] = ast.get_docstring(node)
        elif isinstance(node, ast.ClassDef):
            found[node.name] = ast.get_docstring(node)
            for method in node.body:
                if isinstance(method, ast.FunctionDef):
                    found[f"{node.name}.{method.name}"] = ast.get_docstring(method)

    for where, expected in _expected_docstrings(spec).items():
        assert found.get(where) == expected, (
            f"{where}'s docstring is not the one the signature generates:\n"
            f"{found.get(where)!r}\nshould be\n{expected!r}"
        )


def test_its_examples_give_the_output_they_show(
    spec: KataSpec, kata_directory: Path
) -> None:
    """Every example on the page, run against the reference solution.

    An example is a claim about the right answer, printed where a solver will
    compare their own output against it -- so a wrong one sends somebody
    debugging code that works (ADR 0022, applied to the page rather than to
    the suite). Compared by `repr` of the plain form rather than by `==`,
    because `==` would accept `1` where the function returns `True`, `2` where
    it returns `2.0` and a list where it returns a tuple, and each of those is a
    difference a solver reading the example would be misled by.
    """
    namespace = _reference_namespace(kata_directory, spec)

    for number, example in enumerate(spec.examples, start=1):
        got, want = _run(example, namespace)

        assert repr(_plain(got)) == repr(_plain(want)), (
            f"example {number} shows {example.output!r}, and the reference "
            f"gives {_plain(got)!r}"
        )
