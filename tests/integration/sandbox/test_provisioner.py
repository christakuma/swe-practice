"""Provisioning, the fixture contract, resume, and what gc can see.

The tests that run real fixtures. They are the slowest in the suite and they are
the ones that would have caught every bug found while building this phase, which
is the trade PLAN.md §9 describes: fast at the bottom, and a thin layer at the
top that actually touches the world.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from practice.adapters.sandbox import (
    SubprocessSandboxProvisioner,
    WorkspaceExistsError,
)
from practice.adapters.sandbox.env import FIXTURE_EPOCH, FIXTURE_STEP
from practice.adapters.sandbox.fixture_runner import FixtureError
from practice.config import content_root
from practice.domain.exercise import ExerciseKind
from practice.domain.ids import AttemptId
from tests.integration.sandbox.conftest import FLAGSHIP, RECOVERY, scenario

if TYPE_CHECKING:
    from pathlib import Path

    from practice.adapters.content import FilesystemContentRepository
    from practice.adapters.sandbox import SubprocessWorkspace
    from practice.domain.exercise import Exercise
    from practice.domain.ids import ExerciseId


# --- what a fixture leaves behind ------------------------------------------


def test_the_fixture_built_a_real_repository(workspace: SubprocessWorkspace) -> None:
    result = workspace.run(["git", "log", "--oneline"], timeout=10)

    assert len(result.stdout.strip().splitlines()) == 3


def test_the_aliases_are_recorded(workspace: SubprocessWorkspace) -> None:
    """`commit_as` appends them, and assertions resolve `@c2` through them.

    Hard-coding hashes into assertions would be unreadable and would break
    whenever a fixture is edited, which is what the alias map exists to avoid
    (PLAN.md §6.1).
    """
    aliases = workspace.aliases()

    assert sorted(aliases) == ["c1", "c2", "c3"]


def test_the_aliases_point_at_real_commits(workspace: SubprocessWorkspace) -> None:
    """An alias that resolved to nothing would make its assertion unfailable."""
    for name, sha in workspace.aliases().items():
        result = workspace.run(["git", "cat-file", "-t", sha.value], timeout=10)

        assert result.stdout.strip() == "commit", name


def test_the_snapshot_records_every_ref(workspace: SubprocessWorkspace) -> None:
    """What makes `ref_unchanged {since: fixture}` possible: the engine can tell
    whether `origin/main` moved during the attempt (PLAN.md §6.1).
    """
    snapshot = workspace.snapshot()

    assert "refs/heads/main" in snapshot
    assert "refs/remotes/origin/main" in snapshot


def test_the_snapshot_includes_head(workspace: SubprocessWorkspace) -> None:
    """Not a ref `for-each-ref` reports, and needed anyway: an exercise asking
    whether the solver ended up back on a branch has to know where HEAD began.
    """
    assert "HEAD" in workspace.snapshot()


def test_the_snapshot_is_taken_after_the_fixture_not_during(
    workspace: SubprocessWorkspace,
) -> None:
    """`recover-a-lost-commit`'s fixture ends by switching branches twice, so a
    snapshot taken mid-run would record a HEAD that never existed at handover.
    """
    head = workspace.run(["git", "rev-parse", "HEAD"], timeout=10).stdout.strip()

    assert workspace.snapshot()["HEAD"].value == head


def test_the_clock_is_left_where_the_fixture_stopped(
    workspace: SubprocessWorkspace,
) -> None:
    """Three commits, so three ticks — and the solver's first commit continues
    from there rather than restarting (PLAN.md §6.1).
    """
    assert int(workspace.layout.clock.read_text().strip()) == (
        FIXTURE_EPOCH + 3 * FIXTURE_STEP
    )


def test_the_fixture_is_copied_in_rather_than_run_in_place(
    workspace: SubprocessWorkspace,
) -> None:
    """So a fixture cannot reach its own siblings.

    `solution.cmds` and the counter-examples are the answers, and they are not
    in the workspace at all.
    """
    assert workspace.layout.fixture.is_file()
    assert workspace.layout.fixture_lib.is_file()
    assert not list(workspace.root.rglob("*.cmds"))


def test_the_answers_are_not_in_the_workspace(
    workspace: SubprocessWorkspace,
) -> None:
    """Stated separately from the test above because it is the property that
    matters and the copying is only how it is achieved.
    """
    assert not list(workspace.repo.rglob("solution*"))


# --- determinism -----------------------------------------------------------


def test_the_same_fixture_twice_produces_the_same_hashes(
    provisioner: SubprocessSandboxProvisioner, flagship: Exercise
) -> None:
    """Run-to-run determinism, which is the half that can be tested on one
    machine. Cross-platform determinism is `content/fixtures.lock`, checked by
    CI on both runners.
    """
    first = provisioner.provision(flagship, AttemptId.parse(_an_id(1)))
    first_aliases = dict(first.aliases())
    first.dispose()

    second = provisioner.provision(flagship, AttemptId.parse(_an_id(2)))
    second_aliases = dict(second.aliases())
    second.dispose()

    assert first_aliases == second_aliases


def test_the_trees_match_the_hand_run_recorded_in_the_plan(
    workspace: SubprocessWorkspace,
) -> None:
    """PLAN.md §6.6 records `0b2626fa` as c2's tree, from a run done by hand
    before any of this code existed.

    A tree hash does not depend on the author or committer identity, so it is
    the one value from that record this suite can check directly — the commit
    hashes in §6.6 came from a different pinned identity and are expected to
    differ. It is a genuinely independent confirmation that the pinned
    environment reproduces what was validated in §6.6, rather than merely
    reproducing itself.
    """
    c2 = workspace.aliases()["c2"]

    result = workspace.run(["git", "rev-parse", f"{c2.value}^{{tree}}"], timeout=10)

    assert result.stdout.strip().startswith("0b2626fa")


def test_a_fixture_commits_under_the_pinned_identity(
    workspace: SubprocessWorkspace,
) -> None:
    """Both identities, because both are inputs to the hash (PLAN.md §6.1)."""
    result = workspace.run(["git", "log", "-1", "--format=%an|%ae|%cn|%ce"], timeout=10)

    assert result.stdout.strip() == (
        "Practice Fixture|fixture@practice.invalid|"
        "Practice Fixture|fixture@practice.invalid"
    )


def test_no_fixture_commit_has_a_wall_clock_date(
    workspace: SubprocessWorkspace,
) -> None:
    """Every commit date has to come from the pinned clock.

    A fixture that committed without `commit_as` would otherwise get the current
    time and break the lock file on the next run — which is why the dates are
    exported before bash starts, not only inside the helper.
    """
    result = workspace.run(["git", "log", "--format=%at"], timeout=10)
    dates = [int(line) for line in result.stdout.split()]

    assert dates == sorted(dates, reverse=True)
    assert all((date - FIXTURE_EPOCH) % FIXTURE_STEP == 0 for date in dates), (
        f"a commit was not dated by the clock: {dates}"
    )


# --- katas -----------------------------------------------------------------


def test_a_kata_gets_a_workspace_with_its_files(
    provisioner: SubprocessSandboxProvisioner,
    library: FilesystemContentRepository,
    attempt_id: AttemptId,
) -> None:
    """Treated as a kind of workspace rather than a special case, so the Phase 4
    kata runner does not grow its own parallel notion of one.
    """
    kata = library.get(_a_kata_id(library))
    assert kata is not None

    workspace = provisioner.provision(kata, attempt_id)
    try:
        names = sorted(path.name for path in workspace.repo.iterdir())

        assert "stub.py" in names
        assert "tests.py" in names
    finally:
        workspace.dispose()


def test_a_katas_reference_solution_is_not_copied_in(
    provisioner: SubprocessSandboxProvisioner,
    library: FilesystemContentRepository,
    attempt_id: AttemptId,
) -> None:
    """An answer key inside the exam. Phase 4 copies it separately, for the
    content test that proves the reference passes.
    """
    kata = library.get(_a_kata_id(library))
    assert kata is not None

    workspace = provisioner.provision(kata, attempt_id)
    try:
        assert not (workspace.repo / "solution.py").exists()
    finally:
        workspace.dispose()


def test_a_kata_has_no_repository(
    provisioner: SubprocessSandboxProvisioner,
    library: FilesystemContentRepository,
    attempt_id: AttemptId,
) -> None:
    """There is nothing to grade by repository state, so there is no repository.
    Running `git init` anyway would invite an assertion that cannot mean
    anything.
    """
    kata = library.get(_a_kata_id(library))
    assert kata is not None

    workspace = provisioner.provision(kata, attempt_id)
    try:
        assert not (workspace.repo / ".git").exists()
    finally:
        workspace.dispose()


# --- resume and collision --------------------------------------------------


def test_provisioning_twice_for_one_attempt_is_refused(
    provisioner: SubprocessSandboxProvisioner,
    flagship: Exercise,
    attempt_id: AttemptId,
) -> None:
    """The only two things it can mean are both bad to guess at: an attempt is
    open in another tab, or a previous process died with work still on disk.
    Clobbering it would make the resume-or-abandon promise a lie (PLAN.md §8.1).
    """
    workspace = provisioner.provision(flagship, attempt_id)
    try:
        with pytest.raises(WorkspaceExistsError):
            provisioner.provision(flagship, attempt_id)
    finally:
        workspace.dispose()


def test_attach_reopens_the_work_in_progress(
    provisioner: SubprocessSandboxProvisioner,
    flagship: Exercise,
    attempt_id: AttemptId,
) -> None:
    """The resume half of PLAN.md §8.1. An interrupted session is neither
    silently lost nor silently resurrected — and resuming must not re-run the
    fixture over the top of the solver's work.
    """
    first = provisioner.provision(flagship, attempt_id)
    first.run(["write", "in-progress.md", "my work so far"], timeout=10)

    resumed = provisioner.attach(flagship, attempt_id)

    assert resumed is not None
    try:
        assert resumed.read_file("in-progress.md") == "my work so far\n"
        assert resumed.aliases() == first.aliases()
    finally:
        resumed.dispose()


def test_a_resumed_attempt_continues_the_clock(
    provisioner: SubprocessSandboxProvisioner,
    flagship: Exercise,
    attempt_id: AttemptId,
) -> None:
    """The reason the clock is a file (PLAN.md §6.1).

    A resumed attempt runs in a process that did not provision the workspace, so
    an in-memory clock would restart the history at the fixture epoch and date a
    new commit before the ones it follows.
    """
    first = provisioner.provision(flagship, attempt_id)
    first.run(["git", "status"], timeout=10)
    before = int(first.layout.clock.read_text().strip())

    resumed = provisioner.attach(flagship, attempt_id)
    assert resumed is not None
    try:
        resumed.run(["git", "status"], timeout=10)

        assert int(resumed.layout.clock.read_text().strip()) > before
    finally:
        resumed.dispose()


def test_attaching_to_nothing_is_not_an_error(
    provisioner: SubprocessSandboxProvisioner,
    flagship: Exercise,
    attempt_id: AttemptId,
) -> None:
    """An attempt whose workspace has been collected is a normal thing for the
    caller to decide about, not a fault.
    """
    assert provisioner.attach(flagship, attempt_id) is None


# --- a fixture that fails --------------------------------------------------


def test_a_failing_fixture_raises_with_its_output(
    tmp_path: Path, library: FilesystemContentRepository, attempt_id: AttemptId
) -> None:
    """A fixture that failed halfway is the only evidence of why.

    So the workspace is deliberately *not* disposed of, and the error says where
    to go and look.
    """
    broken = tmp_path / "content"
    _copy_library_shell(broken)
    (broken / "git" / "revert-a-pushed-commit" / "fixture.sh").write_text(
        '#!/usr/bin/env bash\nsource "$PRACTICE_FIXTURE_LIB"\n'
        "echo 'about to fail' >&2\nexit 3\n",
        encoding="utf-8",
        newline="",
    )
    provisioner = SubprocessSandboxProvisioner(
        content_root=broken, workspace_root=tmp_path / "ws"
    )
    exercise = scenario(library, FLAGSHIP)

    with pytest.raises(FixtureError) as raised:
        provisioner.provision(exercise, attempt_id)

    assert "about to fail" in str(raised.value)
    assert raised.value.root.is_dir(), "the workspace should be kept for inspection"


# --- what gc can see -------------------------------------------------------


def test_a_workspace_describes_itself(
    provisioner: SubprocessSandboxProvisioner,
    flagship: Exercise,
    attempt_id: AttemptId,
) -> None:
    """Written as JSON into the workspace because the reader is a different
    process: `practice gc` enumerates directories left by sessions that exited.
    """
    workspace = provisioner.provision(flagship, attempt_id)
    try:
        (record,) = provisioner.workspaces()

        assert record.attempt_id == attempt_id
        assert record.exercise_id == flagship.id
        assert record.created_at
        assert record.size_bytes() > 0
    finally:
        workspace.dispose()


def test_an_undescribed_workspace_is_still_reported(
    provisioner: SubprocessSandboxProvisioner,
    flagship: Exercise,
    attempt_id: AttemptId,
) -> None:
    """An interrupted provision is precisely the leftover gc exists to find, so
    unreadable metadata must not make it invisible.
    """
    workspace = provisioner.provision(flagship, attempt_id)
    try:
        workspace.layout.metadata.unlink()

        (record,) = provisioner.workspaces()

        assert not record.is_described
        assert record.short_id == attempt_id.short
    finally:
        workspace.dispose()


def test_no_workspaces_before_anything_is_provisioned(
    provisioner: SubprocessSandboxProvisioner,
) -> None:
    assert provisioner.workspaces() == ()


def test_a_disposed_workspace_is_no_longer_reported(
    provisioner: SubprocessSandboxProvisioner,
    flagship: Exercise,
    attempt_id: AttemptId,
) -> None:
    """An attempt disposes of its own workspace when it is submitted or
    abandoned, which is why gc has nothing to do in the normal case.
    """
    provisioner.provision(flagship, attempt_id).dispose()

    assert provisioner.workspaces() == ()


# --- helpers ---------------------------------------------------------------


def _an_id(index: int) -> str:
    return f"3f2a1b0c-0000-4000-8000-{index:012d}"


def _a_kata_id(library: FilesystemContentRepository) -> ExerciseId:
    """The first kata in the library, so adding more does not break this."""
    for exercise in library.list_exercises():
        if exercise.kind is ExerciseKind.KATA:
            return exercise.id
    pytest.fail("the library has no kata")


def _copy_library_shell(destination: Path) -> None:
    """Copy the real library so one fixture can be replaced with a broken one.

    A copy rather than a hand-built exercise, because the thing under test is
    what happens to a *real* exercise whose fixture fails, and a synthetic one
    would be testing the synthetic one.
    """
    shutil.copytree(content_root(), destination)


def test_the_recovery_fixture_leaves_unreachable_commits(
    provisioner: SubprocessSandboxProvisioner,
    library: FilesystemContentRepository,
    attempt_id: AttemptId,
) -> None:
    """The whole premise of `recover-a-lost-commit`, asserted.

    Two commits destroyed by `reset --hard`, recoverable only through the
    reflog. If garbage collection or reflog expiry were ever enabled in the
    pinned config, this exercise would quietly become unsolvable — and this is
    the test that would say so.
    """
    exercise = scenario(library, RECOVERY)
    workspace = provisioner.provision(exercise, attempt_id)
    try:
        lost = workspace.aliases()["c3"]

        reachable = workspace.run(
            ["git", "log", "--oneline", "--all"], timeout=10
        ).stdout
        assert lost.short not in reachable, "the fixture did not destroy the work"

        exists = workspace.run(["git", "cat-file", "-t", lost.value], timeout=10)
        assert exists.stdout.strip() == "commit", "the lost commit is unrecoverable"
    finally:
        workspace.dispose()
