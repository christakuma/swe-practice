"""Running a kata's hidden test suite against a solver's source.

One subprocess, fully pinned, and the pinning is the whole content of this
module. Every argument in `_ARGV` and every file in `_MECHANISM` is there
because leaving it to a default lets something outside the workspace change how
a kata grades.

**The invocation, and why each piece of it** (PLAN.md §7, corrected by running
it):

* `sys.executable` — the app's own interpreter. A kata is graded by the Python
  that is running the grader, not by whatever `python` means on this `PATH`.
* `-I` — isolated mode: no user site-packages, no `PYTHONPATH`, no `PYTHON*`
  environment variables at all. A stray `PYTHONSTARTUP` or a half-installed
  `sitecustomize` on the solver's machine cannot change a verdict.
* `-X utf8` — **because `-I` implies `-E`**, which drops `PYTHONIOENCODING`
  along with everything else. The sandbox environment pins `LC_ALL=C` for git's
  sake, under which the locale encoding is ASCII and a non-ASCII character in
  an assertion message would raise inside pytest's own reporting. `-X` is a
  command-line option, so it survives `-E`.
* `-c pytest.ini` — pins the config file, and with it the rootdir. Without it
  pytest walks *upwards* from the workspace looking for an ini file, and would
  obey the `addopts` of any project that happened to be an ancestor of the user
  cache directory — including this one, whose `addopts` carries `--cov`.
* `--color=no` — proven necessary, not defensive. pytest colours assertion
  diffs from `TERM`, so `assert (0, 0) == (1, 2)` arrives wrapped in ANSI
  escapes that would be stored in a `CheckReport` and printed as mojibake. Same
  class of problem as `color.ui=false` in the pinned gitconfig.
* `-p no:cacheprovider` — no `.pytest_cache` written into the graded directory.
* `-q --no-header` — the captured output is read by a human only when something
  went wrong, and the banner is never the interesting part of it.

**Why the plugin is copied rather than imported.** `-p` takes a module name and
`-I` implies `-P`, so the workspace is not on `sys.path` when pytest resolves
plugin arguments — the import fails before collection starts. The copied-in
`conftest.py` registers it through `pytest_plugins` instead, and puts the
workspace on `sys.path` explicitly on the way. §7 said `-p practice_report`;
that cannot work, and finding out took one command.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from practice.adapters.kata.report_plugin import REPORT_OPTION, SCHEMA_VERSION
from practice.adapters.sandbox.execution import TIMEOUT_EXIT_CODE

if TYPE_CHECKING:
    from practice.domain.exercise import KataSpec
    from practice.domain.ports import Workspace

__all__ = [
    "CONFTEST",
    "PLUGIN_MODULE",
    "PYTEST_INI",
    "KataRun",
    "PytestKataRunner",
    "TestOutcome",
    "TestRecord",
    "mechanism_files",
    "parse_records",
    "plugin_source",
]

#: What the copied plugin is called inside the workspace. A `practice_` prefix
#: rather than `report_plugin`, because the workspace is on `sys.path` for the
#: graded process and a generic name could shadow something a solution imports.
PLUGIN_MODULE: Final = "practice_report"

#: The solver's source, and the module name `tests.py` imports from.
SOLUTION_MODULE: Final = "solution.py"

#: Where the plugin writes, relative to the workspace.
REPORT_FILE: Final = "report.json"

#: Pins the config file and therefore the rootdir. Empty on purpose: what it is
#: *for* is stopping pytest from finding somebody else's.
PYTEST_INI: Final = """\
# Written by practice. It exists to pin pytest's rootdir to this workspace and
# to stop it discovering the ini file of any project that happens to be an
# ancestor of the user cache directory -- see adapters/kata/pytest_runner.py.
[pytest]
"""

#: Registers the plugin, and puts the workspace on `sys.path`.
#:
#: The `sys.path` line is belt and braces: pytest's default prepend import mode
#: inserts the rootdir when it imports `tests.py`, so `from solution import
#: two_sum` would work without it. It is here anyway because that is a side
#: effect of an import mode that can be changed by a flag, while the thing
#: being relied on -- a kata is one file, importable by name -- is part of the
#: contract (PLAN.md §16, "the `python -I -m pytest` invocation cannot import
#: `solution`").
CONFTEST: Final = f'''\
"""Written by practice. Do not edit; it is rewritten on every run."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# `-p {PLUGIN_MODULE}` cannot be used: python -I implies -P, so this directory
# is not importable when pytest resolves plugin arguments. Declaring it here
# works because pytest has already imported this file by path.
pytest_plugins = ("{PLUGIN_MODULE}",)
'''

#: The arguments after the test file. Order is irrelevant to pytest and fixed
#: here so the command a failure report quotes is the command that ran.
_ARGV: Final = (
    "-c",
    "pytest.ini",
    "-p",
    "no:cacheprovider",
    "-q",
    "--no-header",
    "--color=no",
    REPORT_OPTION,
    REPORT_FILE,
)

#: How much captured output to carry into a verdict when the suite did not run
#: at all. The tail rather than the head: a collection error puts its own
#: traceback last, under the "1 error during collection" line.
_OUTPUT_TAIL: Final = 1500


class TestOutcome(StrEnum):
    """What happened to one test.

    `ERROR` is kept distinct from `FAILED` because they send a solver to
    different files: a failure in the call is a wrong solution, and a failure in
    setup or teardown is a broken test suite.
    """

    # Both this and `TestRecord` are named for what they describe, and the name
    # collides with pytest's own collection rule: a `Test`-prefixed class in a
    # module pytest is collecting is a test class, and one with a constructor is
    # a `PytestCollectionWarning` -- which this project's `filterwarnings =
    # ["error"]` turns into a collection *error* in any test file that imports
    # them. `__test__` is the documented opt-out, and it is preferred here over
    # renaming the types: a kata's hidden suite really is a list of tests, and
    # the domain vocabulary should not bend around a prefix convention.
    __test__ = False

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class TestRecord:
    """One test, as the plugin recorded it."""

    __test__ = False  # see TestOutcome

    nodeid: str
    outcome: TestOutcome
    message: str | None = None
    location: str | None = None
    duration_ms: int = 0
    doc: str | None = None

    @property
    def passed(self) -> bool:
        """Only `PASSED` counts.

        A skipped test is not a pass, which is a deliberate call: a hidden suite
        that skips has not verified the thing it claims to, and reporting that
        as satisfied would quietly narrow what the kata grades.
        """
        return self.outcome is TestOutcome.PASSED

    @property
    def name(self) -> str:
        """The test's name within its module: `test_handles_repeated_values`.

        Everything after the *first* `::`, not the last. A class-based suite
        gives `tests.py::TestSorting::test_empty`, and keeping the class means
        two classes with a `test_empty` each stay distinguishable — taking the
        last segment would collapse them into one name and leave the labels in
        a verdict saying the same thing twice.
        """
        return self.nodeid.partition("::")[2] or self.nodeid


@dataclass(frozen=True, slots=True)
class KataRun:
    """Everything one grading run produced.

    `tests` empty means the suite never ran — a collection error, a timeout, a
    missing report. That is a different thing from every test failing, and the
    grader reports it differently, so the distinction is kept here rather than
    flattened into "nothing passed".
    """

    tests: tuple[TestRecord, ...]
    exit_code: int
    duration_ms: int = 0
    exit_status: int | None = None
    output: str = ""

    @property
    def ran(self) -> bool:
        return bool(self.tests)

    @property
    def timed_out(self) -> bool:
        """Inferred from the exit code, which is where the sandbox puts it.

        `CommandResult` drops the sandbox's `timed_out` flag on the way into the
        domain, deliberately — 124 is the invented exit code that carries the
        same information, and it is the one GNU `timeout` uses.
        """
        return self.exit_code == TIMEOUT_EXIT_CODE

    @property
    def failures(self) -> tuple[TestRecord, ...]:
        return tuple(record for record in self.tests if not record.passed)

    def why_it_did_not_run(self, spec: KataSpec) -> str:
        """A single line naming the reason, for the synthesised check report.

        Only meaningful when `ran` is false. Written here rather than in the
        grader because it is the runner that knows what the exit codes mean.
        """
        if self.timed_out:
            return (
                f"the test suite was killed after "
                f"{spec.time_limit_seconds}s without finishing"
            )
        if self.exit_status is None:
            return f"the test suite wrote no report (pytest exited {self.exit_code})"
        return (
            f"the test suite collected no tests (pytest exited {self.exit_status}); "
            f"this is a broken suite or a solution that cannot be imported"
        )


class PytestKataRunner:
    """Runs a kata's tests in a provisioned workspace.

    Holds no state about any one attempt: the workspace is an argument, so one
    runner serves every attempt in the process and the composition root builds
    exactly one.
    """

    __slots__ = ("_plugin_source",)

    def __init__(self) -> None:
        # Read once, at construction. The alternative is reading the file on
        # every submission, which makes grading depend on the installed package
        # still being on disk half an hour into a session.
        self._plugin_source = plugin_source()

    def run(self, workspace: Workspace, spec: KataSpec, source: str) -> KataRun:
        """Install the mechanism, write the source, run the suite, read the report.

        Every file is written on every run rather than once at provisioning.
        They are this module's contract with the subprocess, not the exercise's
        content, and rewriting them means a resumed attempt cannot be graded by
        a plugin that was copied in by an older version of this file.
        """
        self._install(workspace)
        workspace.write_file(SOLUTION_MODULE, source)

        result = workspace.run_tool(
            [
                sys.executable,
                "-I",
                "-X",
                "utf8",
                "-m",
                "pytest",
                spec.tests,
                *_ARGV,
            ],
            timeout=spec.time_limit_seconds,
        )
        document = self._read_report(workspace)

        return KataRun(
            tests=parse_records(document),
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            exit_status=_exit_status(document),
            output=_tail(result.stdout, result.stderr),
        )

    def _install(self, workspace: Workspace) -> None:
        workspace.write_file(f"{PLUGIN_MODULE}.py", self._plugin_source)
        workspace.write_file("conftest.py", CONFTEST)
        workspace.write_file("pytest.ini", PYTEST_INI)

    def _read_report(self, workspace: Workspace) -> dict[str, Any] | None:
        """`None` when there is nothing readable there.

        Tolerant rather than strict, because every way this fails is a way the
        suite did not run: killed before `sessionfinish`, interrupted
        mid-write, or written by a plugin copy whose shape this module no longer
        recognises. The grader turns `None` into one failing check that says so,
        which is a verdict; an exception here would be a traceback in the panel
        instead (PLAN.md §6.5).
        """
        try:
            document = json.loads(workspace.read_file(REPORT_FILE))
        except (OSError, ValueError):
            return None
        if not isinstance(document, dict):
            return None
        if document.get("version") != SCHEMA_VERSION:
            return None
        return document


def plugin_source() -> str:
    """The plugin's own source, to be copied into a workspace.

    Read off disk rather than held as a string so that the file linted, typed
    and imported by this project is byte-for-byte the file the subprocess loads.
    A second copy as a literal would drift, and the symptom would be a grading
    bug that cannot be reproduced by reading the plugin.
    """
    return (Path(__file__).parent / "report_plugin.py").read_text(encoding="utf-8")


def parse_records(document: dict[str, Any] | None) -> tuple[TestRecord, ...]:
    """Turn the plugin's JSON into typed records, skipping what makes no sense.

    A malformed entry is dropped rather than fatal, for the same reason
    `read_sha_map` skips a bad line: the writer is trusted code, so a bad entry
    means a bug in the plugin — and that should cost one check its report, not
    take down the grading pass with a `KeyError`.
    """
    if document is None:
        return ()
    entries = document.get("tests")
    if not isinstance(entries, list):
        return ()

    records = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        nodeid = entry.get("nodeid")
        if not isinstance(nodeid, str) or not nodeid:
            continue
        try:
            outcome = TestOutcome(str(entry.get("outcome")))
        except ValueError:
            continue
        records.append(
            TestRecord(
                nodeid=nodeid,
                outcome=outcome,
                message=_text(entry.get("message")),
                location=_text(entry.get("location")),
                duration_ms=_duration(entry.get("duration_ms")),
                doc=_text(entry.get("doc")),
            )
        )
    return tuple(records)


def _exit_status(document: dict[str, Any] | None) -> int | None:
    if document is None:
        return None
    status = document.get("exit_status")
    return status if isinstance(status, int) else None


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _duration(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _tail(stdout: str, stderr: str) -> str:
    """The last of whatever the process said, both streams, stdout first."""
    captured = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part)
    return captured[-_OUTPUT_TAIL:]


def mechanism_files() -> tuple[str, ...]:
    """Every file the runner writes that is not the solver's source.

    Exported so a test can assert the set, and so the Phase 7 editor knows
    which files in a workspace are plumbing rather than something to show.
    """
    return (f"{PLUGIN_MODULE}.py", "conftest.py", "pytest.ini", REPORT_FILE)
