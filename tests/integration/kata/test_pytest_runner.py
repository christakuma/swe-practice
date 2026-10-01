"""The pinned pytest invocation, run for real.

Everything here is about the subprocess: that it starts, that it can import a
one-file solution under `-I`, that the plugin it loads writes a report, and that
the five things pinned in `pytest_runner._ARGV` are actually pinned. The mapping
from records to reports is unit-tested against a stub; this is the half that
needs a process.

**The isolation tests are the ones worth keeping.** Each corresponds to a way
the invocation went wrong when it was first written — `-p` not resolving under
isolated mode, ANSI escapes arriving inside an assertion message, pytest finding
this project's own `pyproject.toml` by walking upwards. None of the three was
visible on the page, and all three took one command to find (PLAN.md §16).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.adapters.kata.pytest_runner import (
    CONFTEST,
    PLUGIN_MODULE,
    TestOutcome,
    mechanism_files,
    plugin_source,
)
from practice.adapters.sandbox.execution import TIMEOUT_EXIT_CODE

if TYPE_CHECKING:
    from practice.adapters.kata import PytestKataRunner
    from practice.adapters.sandbox import SubprocessWorkspace
    from practice.domain.exercise import KataSpec
    from tests.integration.kata.conftest import Provision

WRONG = """\
def two_sum(numbers, target):
    '''Looks up the complement without excluding the element's own position.'''
    for index, value in enumerate(numbers):
        complement = target - value
        if complement in numbers:
            return (index, numbers.index(complement))
    raise ValueError("no pair")
"""

LOOPS_FOREVER = "def two_sum(numbers, target):\n    while True:\n        pass\n"

NOT_PYTHON = "this is not python at all\n"


# --- the happy path --------------------------------------------------------


def test_the_reference_solution_passes_every_test(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
    reference: str,
) -> None:
    run = runner.run(workspace, spec, reference)

    assert run.ran
    assert run.exit_code == 0
    assert run.failures == (), [record.message for record in run.failures]
    assert len(run.tests) >= 2


def test_the_stub_fails_every_test(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
    stub: str,
) -> None:
    """A suite that passes an unimplemented stub is a broken suite (§9). Here
    that is a property of the *runner* — the content suite asserts it per kata.
    """
    run = runner.run(workspace, spec, stub)

    assert run.ran
    assert run.exit_code != 0
    assert len(run.failures) == len(run.tests)
    assert all(record.outcome is TestOutcome.FAILED for record in run.tests), [
        record.outcome for record in run.tests
    ]


def test_a_wrong_solution_fails_the_tests_it_should_and_passes_the_rest(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
) -> None:
    """The partial case, which is the one real solvers produce.

    `WRONG` is the plausible mistake the kata's own `tests.py` was written to
    catch: it pairs an element with itself. If it failed *everything* the suite
    would not be discriminating, and if it passed everything the suite would be
    useless — so this pins both.

    Asserted on `TestRecord.name` rather than on a derived check id: how a name
    becomes an id is the grader's business, and a runner test should speak the
    runner's own vocabulary.
    """
    run = runner.run(workspace, spec, WRONG)

    failed = {record.name for record in run.failures}
    passed = {record.name for record in run.tests if record.passed}

    assert "test_does_not_pair_an_element_with_itself" in failed
    assert "test_finds_the_pair_in_a_short_list" in passed


def test_a_failure_carries_a_message_and_a_line(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
    stub: str,
) -> None:
    """What ends up in the verdict panel: a reason and somewhere to look."""
    failure = runner.run(workspace, spec, stub).failures[0]

    assert failure.message == "NotImplementedError"
    assert failure.location == "solution.py:15"
    assert failure.duration_ms >= 0


def test_the_docstrings_come_back_as_labels(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
    reference: str,
) -> None:
    """The plugin's one non-bookkeeping job (PLAN.md §7)."""
    run = runner.run(workspace, spec, reference)

    assert all(record.doc for record in run.tests), [
        record.nodeid for record in run.tests if not record.doc
    ]


# --- what the pinning buys -------------------------------------------------


def test_an_assertion_message_carries_no_ansi_escapes(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
) -> None:
    """`--color=no`, and it is not defensive: pytest colours assertion diffs
    from `TERM`, so without it `assert (0, 0) == (1, 2)` arrives wrapped in
    escape codes that get stored in a `CheckReport` and printed as mojibake.
    Same class of problem as `color.ui=false` in the pinned gitconfig.
    """
    run = runner.run(workspace, spec, WRONG)

    messages = [record.message or "" for record in run.failures]
    assert messages
    assert not any("\x1b[" in message for message in messages), messages


def test_the_runner_does_not_inherit_this_project_s_pytest_config(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
    reference: str,
) -> None:
    """`-c pytest.ini` pins the rootdir.

    Without it pytest walks upwards looking for an ini file and would obey the
    `addopts` of whatever project happens to be above the workspace — including
    this one, whose `addopts` carries `--cov` and whose `filterwarnings` is
    `error`. The workspace's own ini is empty, so a clean run proves nothing
    else was picked up.
    """
    run = runner.run(workspace, spec, reference)

    assert workspace.read_file("pytest.ini").strip().endswith("[pytest]")
    assert "--cov" not in run.output
    assert run.exit_code == 0


def test_the_mechanism_files_are_the_copied_plugin_and_nothing_imported(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
    reference: str,
) -> None:
    """The plugin in the workspace is byte-for-byte the file this project lints
    and type-checks. A second copy as a string literal would drift, and the
    symptom would be a grading bug invisible from reading the plugin.
    """
    runner.run(workspace, spec, reference)

    assert workspace.read_file(f"{PLUGIN_MODULE}.py") == plugin_source()
    assert workspace.read_file("conftest.py") == CONFTEST
    for name in mechanism_files():
        assert (workspace.repo / name).is_file(), name


def test_the_mechanism_is_rewritten_on_every_run(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
    reference: str,
) -> None:
    """A resumed attempt must not be graded by a plugin copied in by an older
    version of the runner, so the files are the runner's contract rather than
    the provisioner's.
    """
    workspace.write_file(f"{PLUGIN_MODULE}.py", "raise SystemExit('stale plugin')\n")

    run = runner.run(workspace, spec, reference)

    assert run.ran
    assert run.failures == ()


def test_the_solver_s_source_is_what_runs(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
    reference: str,
) -> None:
    """Written to `solution.py`, which is the module the hidden tests import.

    The stub stays beside it untouched: it is the starting point a solver is
    shown, not the thing that is graded.
    """
    runner.run(workspace, spec, reference)

    assert workspace.read_file("solution.py") == reference
    assert workspace.read_file(spec.stub) != reference


# --- when the suite does not run ------------------------------------------


def test_a_solution_that_never_returns_is_killed_by_the_time_limit(
    runner: PytestKataRunner,
    provision: Provision,
    kata_spec_with_a_short_limit: KataSpec,
) -> None:
    """The time limit is enforced at the subprocess level rather than through
    `pytest-timeout`, so this also proves the process tree is actually taken —
    on Windows via `taskkill /T /F`, which is what lets the workspace be
    deleted afterwards (ADR 0005).
    """
    workspace = provision()

    run = runner.run(workspace, kata_spec_with_a_short_limit, LOOPS_FOREVER)

    assert not run.ran
    assert run.timed_out
    assert run.exit_code == TIMEOUT_EXIT_CODE
    assert "killed after" in run.why_it_did_not_run(kata_spec_with_a_short_limit)


def test_a_solution_that_cannot_be_imported_collects_nothing(
    runner: PytestKataRunner,
    workspace: SubprocessWorkspace,
    spec: KataSpec,
) -> None:
    """Not the same thing as every test failing, and the output says why.

    This is the case `-I` makes possible to get wrong: the solution is imported
    by name from the workspace, and if the workspace were not on `sys.path` a
    *correct* solution would land here too (PLAN.md §16).
    """
    run = runner.run(workspace, spec, NOT_PYTHON)

    assert not run.ran
    assert not run.timed_out
    assert run.exit_status != 0
    assert "collected no tests" in run.why_it_did_not_run(spec)
    # pytest's own line, rather than the name of whichever exception the junk
    # source happens to raise: `this is not python at all` is a SyntaxError and
    # `this is not python` is a NameError, and the distinction is not the point.
    assert "error during collection" in run.output
