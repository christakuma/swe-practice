"""Every fixture on disk, actually run.

The half of PLAN.md §9's content suite that Phase 2 could not land. `validate`
proves a scenario is *structurally* valid; this proves its fixture *works* —
that it exits clean, builds a repository, dates its commits by the pinned clock,
and records the aliases its checks refer to.

**The oracle this file used to apologise for is `test_scenarios.py`.** Until
Phase 5 there was no check engine, so nothing could say whether a replayed
reference solution left the repository in the *right* state — and this file said
so loudly and did the next best thing: replay every line and require it to
succeed. That is still here and still worth having, because it catches a
different class of rot. A reference solution with a flag that does not exist,
a path that is not there or a command that needs a shell fails *here*, naming the
line; the same solution arriving at a wrong end state fails in `test_scenarios.py`,
naming the check. Two failures, two different fixes.

Parametrized over the real `content/` directory, so adding an exercise adds test
cases without touching this file. Discovery is shared with `test_scenarios.py`
through `conftest.py`: two copies of "which directories are git scenarios" would
be two chances to disagree, and the way they would disagree is one suite covering
an exercise the other silently skips.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import load_exercise
from practice.adapters.content.validation import discover
from practice.adapters.sandbox import SubprocessSandboxProvisioner, find_bash, find_git
from practice.adapters.sandbox.env import FIXTURE_EPOCH, FIXTURE_STEP
from practice.adapters.sandbox.fixture_lock import (
    LOCK_FILENAME,
    compare,
    fingerprint_library,
    lock_path,
    parse,
)
from practice.adapters.sandbox.provisioner import FIXTURE_LIB_PATH
from practice.domain.checks.evaluation import alias_name
from practice.domain.commands import parse_command_list
from practice.domain.exercise import GitScenarioSpec
from practice.domain.ids import AttemptId
from tests.content.conftest import CONTENT_ROOT, identify, scenario_directories

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from practice.adapters.sandbox import SubprocessWorkspace
    from practice.domain.exercise import Exercise

SCENARIO_DIRECTORIES = scenario_directories()


@pytest.fixture(scope="session")
def tools() -> tuple[Path, Path]:
    """Resolve git and bash once, failing loudly rather than skipping.

    A content suite that silently skips when bash is missing reports success
    exactly as loudly as one that ran every fixture — which is the failure mode
    PLAN.md §9 keeps pointing at.
    """
    return find_git(), find_bash()


@pytest.fixture(params=SCENARIO_DIRECTORIES, ids=identify)
def scenario_directory(request: pytest.FixtureRequest) -> Path:
    directory: Path = request.param
    return directory


@pytest.fixture
def exercise(scenario_directory: Path) -> Exercise:
    return load_exercise(scenario_directory)


@pytest.fixture
def spec(exercise: Exercise) -> GitScenarioSpec:
    assert isinstance(exercise.spec, GitScenarioSpec)
    return exercise.spec


type Provision = Callable[[], SubprocessWorkspace]


@pytest.fixture
def provision(
    tools: tuple[Path, Path], tmp_path: Path, exercise: Exercise
) -> Iterator[Provision]:
    """A factory, because one workspace per test is not always enough.

    Replaying a counter-example mutates the repository, so a test that checks
    several of them needs a fresh workspace for each — otherwise the second one
    starts from wherever the first left off, and what it proves depends on the
    order they happen to be declared in.
    """
    del tools  # requested so a missing tool fails here, not mid-fixture
    provisioner = SubprocessSandboxProvisioner(
        content_root=CONTENT_ROOT, workspace_root=tmp_path / "ws"
    )
    provisioned: list[SubprocessWorkspace] = []

    def build() -> SubprocessWorkspace:
        # The counter varies the *first* eight hex characters, because those are
        # what `AttemptId.short` returns and therefore what names the directory.
        # Varying the last segment instead produces ids that differ and
        # workspaces that collide.
        workspace = provisioner.provision(
            exercise,
            AttemptId.parse(f"{len(provisioned):08x}-0000-4000-8000-000000000000"),
        )
        provisioned.append(workspace)
        return workspace

    try:
        yield build
    finally:
        for workspace in provisioned:
            workspace.dispose()


@pytest.fixture
def provisioned(provision: Provision) -> SubprocessWorkspace:
    """One workspace, for the tests that only need the fixture's end state."""
    return provision()


# --- the walk --------------------------------------------------------------


def test_there_are_fixtures_to_run() -> None:
    """Without this, every parametrized test below is vacuously true."""
    assert SCENARIO_DIRECTORIES


# --- every fixture ---------------------------------------------------------


def test_its_fixture_runs_clean(provisioned: SubprocessWorkspace) -> None:
    """Provisioning raises `FixtureError` on a non-zero exit, so reaching here
    is the assertion. Named as a test anyway, because the failure it produces
    names the exercise.
    """
    assert provisioned.repo.is_dir()


def test_its_fixture_builds_a_repository(provisioned: SubprocessWorkspace) -> None:
    result = provisioned.run(["git", "rev-parse", "--git-dir"], timeout=10)

    assert result.succeeded


def test_its_fixture_leaves_a_clean_worktree(
    provisioned: SubprocessWorkspace,
) -> None:
    """An exercise that starts dirty is almost always a fixture bug, and a
    `worktree_clean` check on it would pass or fail for the wrong reason.

    Where an exercise genuinely wants to start mid-conflict, this is the test
    that has to be taught about it — which is the right way round, because that
    is a deliberate authoring decision and should not be silently available.
    """
    result = provisioned.run(["git", "status", "--porcelain"], timeout=10)

    assert result.stdout == ""


def test_every_alias_its_checks_name_exists(
    provisioned: SubprocessWorkspace, spec: GitScenarioSpec
) -> None:
    """A check referring to `@c4` in a fixture that stops at `c3` can never
    pass, and nothing else would notice: the assertion simply fails every time,
    which looks exactly like a solver getting it wrong.

    Which parameters *are* aliases comes from `alias_name`, the same function
    `resolve` uses, rather than from a `startswith("@")` here. The two disagreed
    until `publish-a-branch-for-review` wrote `{ref: "@{u}"}` — a git revision,
    not an alias — and failed this test while grading correctly (§16).
    """
    available = set(provisioned.aliases())
    for check in spec.checks:
        for value in check.params.values():
            if not isinstance(value, str):
                continue
            alias = alias_name(value)
            if alias is not None:
                assert alias in available, f"{check.id} names {value}"


def test_its_commits_are_dated_by_the_pinned_clock(
    provisioned: SubprocessWorkspace,
) -> None:
    """A fixture that commits without `commit_as` gets wall-clock dates, and
    would break the lock file on the next run for no visible reason.
    """
    result = provisioned.run(["git", "log", "--all", "--format=%at"], timeout=10)
    dates = [int(line) for line in result.stdout.split()]

    assert dates
    assert all((date - FIXTURE_EPOCH) % FIXTURE_STEP == 0 for date in dates)


def test_its_reference_solution_replays_without_errors(
    provisioned: SubprocessWorkspace, spec: GitScenarioSpec, scenario_directory: Path
) -> None:
    """Every line of `solution.cmds`, run through the real sandbox.

    Narrower than `test_scenarios.py` and not subsumed by it: that one asks
    whether the end state is right, and this one asks whether the list can run at
    all. The failure names the line, because "the reference solution is broken" is
    not a useful thing to read — and a list that dies on line one would otherwise
    reach the graded replay and fail every check at once.

    **`reference_failing_commands` is why this counts instead of asserting.** Three
    collaboration scenarios have an answer that begins when a command fails: a
    conflicting `git merge`, a `git rebase` that stops partway, a push rejected as
    non-fast-forward. All exit 1, and before that field existed those exercises
    could not be authored at all. An exercise declares how many of its reference
    lines are expected to fail and the count has to match **exactly** — so a
    mistyped flag in a conflict scenario is still a failure here, naming its line,
    which a blanket per-exercise exemption would have waved through.
    """
    text = (scenario_directory / spec.reference).read_text(encoding="utf-8")
    failed = []
    for command in parse_command_list(text):
        result = provisioned.run(command.argv, timeout=spec.command_timeout_seconds)
        if not result.succeeded:
            failed.append(
                f"{spec.reference}:{command.lineno}: {command.text}\n"
                f"      exit {result.exit_code}\n{result.stderr}"
            )

    assert len(failed) == spec.reference_failing_commands, (
        f"{len(failed)} reference command(s) exited non-zero, and the exercise "
        f"declares reference_failing_commands: "
        f"{spec.reference_failing_commands}\n" + "\n".join(failed)
    )


def test_its_reference_solution_fits_the_command_budget(
    provisioned: SubprocessWorkspace, spec: GitScenarioSpec, scenario_directory: Path
) -> None:
    """A reference that needs more commands than the exercise allows makes it
    unsolvable, and `validate` only counts the lines — this counts what the
    sandbox actually ran, which is the number the `Attempt` policy enforces.
    """
    text = (scenario_directory / spec.reference).read_text(encoding="utf-8")
    commands = parse_command_list(text)

    assert len(commands) <= spec.max_commands
    assert provisioned.repo.is_dir()


def test_each_counter_example_replays_far_enough_to_be_wrong(
    provision: Provision, spec: GitScenarioSpec, scenario_directory: Path
) -> None:
    """A counter-example has to actually *run*, or it fails its declared checks
    for the wrong reason.

    That is the rot PLAN.md §5.4 describes: a naive list that errors out on line
    one still "fails the check it declares", and CI would be none the wiser. The
    counter-examples are replayed in separate workspaces from the reference, so
    the ordering of these tests cannot matter.

    Note the assertion is not that every command succeeds. Some counter-examples
    are *meant* to hit an error — that is sometimes the lesson. What is asserted
    is that the list runs to the end without the sandbox refusing a line, which
    is the failure that would be an authoring bug rather than a teaching point.
    """
    for example in spec.counter_examples:
        workspace = provision()
        text = (scenario_directory / example.file).read_text(encoding="utf-8")
        commands = parse_command_list(text)

        assert commands, f"{example.file} holds no commands"
        for command in commands:
            # Raises CommandRejectedError if the line is not legal here, which
            # is the thing being ruled out.
            workspace.run(command.argv, timeout=spec.command_timeout_seconds)


# --- the lock file ---------------------------------------------------------


def test_the_lock_file_matches_the_library() -> None:
    """The Phase 3 exit criterion, in the suite rather than only in the CLI.

    Duplicates `practice fixtures --check` deliberately, for the reason the CI
    `validate` step is duplicated: what the command adds is proof that the
    command itself works, and what this adds is a failure message that names the
    exercise inside a test report.
    """
    lock = lock_path(CONTENT_ROOT)
    assert lock.is_file(), (
        f"{LOCK_FILENAME} is missing; run `practice fixtures --write`"
    )

    problems = compare(
        parse(lock.read_text(encoding="utf-8")),
        fingerprint_library(_all_exercises(), content_root=CONTENT_ROOT),
    )

    assert problems == (), "\n".join(problems)


def test_the_lock_file_covers_every_scenario() -> None:
    """A lock file that silently omitted an exercise would make its determinism
    claim vacuous while still reporting green.
    """
    locked = {
        entry.exercise_id
        for entry in parse(lock_path(CONTENT_ROOT).read_text(encoding="utf-8"))
    }

    assert locked == {identify(directory) for directory in SCENARIO_DIRECTORIES}


def _all_exercises() -> list[Exercise]:
    return [load_exercise(directory) for directory in discover(CONTENT_ROOT)]


def test_the_fixture_library_is_shared_rather_than_copied() -> None:
    """One `commit_as`, so every fixture's commits are made the same way.

    A fixture that defined its own helper would date commits differently and
    produce hashes nothing could reproduce — and it would pass every other test
    in this file.
    """
    for directory in SCENARIO_DIRECTORIES:
        spec = load_exercise(directory).spec
        assert isinstance(spec, GitScenarioSpec)
        text = (directory / spec.fixture).read_text(encoding="utf-8")

        assert "PRACTICE_FIXTURE_LIB" in text, identify(directory)


def test_the_shared_library_is_where_the_provisioner_looks_for_it() -> None:
    """The provisioner copies it in by a hard-coded relative path, so a rename
    would break every git exercise at once with a `FileNotFoundError`.
    """
    assert (CONTENT_ROOT / FIXTURE_LIB_PATH).is_file()
