"""`practice fixtures` and `practice gc`, driven through Typer's runner.

Integration rather than unit for the reason the `validate` suite gives: the
whole job of both commands is to read what is on disk and say what is there, and
the exit code is the contract CI depends on. A test that stubbed the filesystem
would verify neither.

`fixtures --check` against the real library is the slowest test in the project,
because it runs every fixture. It is also the Phase 3 exit criterion, so it runs
on every invocation rather than behind a marker.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from practice.adapters.content import FilesystemContentRepository
from practice.adapters.sandbox import SubprocessSandboxProvisioner
from practice.adapters.sandbox.fixture_lock import LOCK_FILENAME
from practice.config import content_root
from practice.domain.ids import AttemptId, ExerciseId
from practice.interface.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.exercise import Exercise

FLAGSHIP = ExerciseId("git/revert-a-pushed-commit")

runner = CliRunner()


def run(*arguments: str) -> tuple[int, str]:
    result = runner.invoke(app, list(arguments))
    return result.exit_code, result.output


@pytest.fixture
def copied_library(tmp_path: Path) -> Path:
    """The real library, copied so a fixture or the lock file can be broken.

    A copy rather than a synthetic library, because what these tests are about
    is the real exercises: a hand-built one would prove the command works on
    hand-built exercises.
    """
    destination = tmp_path / "content"
    shutil.copytree(content_root(), destination)
    return destination


# --- practice fixtures -----------------------------------------------------


def test_the_shipped_fixtures_match_the_lock_file() -> None:
    """The Phase 3 exit criterion, as far as one machine can take it.

    The other half is CI running this same command on the other platform. That
    is the whole design: the lock file is the shared reference, so a
    disagreement names which platform diverged instead of just going red.
    """
    code, output = run("fixtures", "--check")

    assert code == 0, output
    assert f"match {LOCK_FILENAME}" in output


def test_it_names_every_exercise_it_checked() -> None:
    """A run that fingerprinted nothing would exit zero just as happily.

    The same hole `test_the_library_was_found` guards in the content suite, and
    the reason this asserts on names rather than on the exit code.
    """
    _, output = run("fixtures", "--check")

    assert "git/revert-a-pushed-commit" in output
    assert "git/recover-a-lost-commit" in output


def test_a_changed_fixture_fails_the_check(copied_library: Path) -> None:
    """What a content author sees after editing a fixture.

    The message has to send them to `--write`, because regenerating and
    reviewing the diff is the correct response and re-running `--check` is not.
    """
    fixture = copied_library / "git" / "revert-a-pushed-commit" / "fixture.sh"
    fixture.write_text(
        fixture.read_text(encoding="utf-8").replace(
            "Add project skeleton and build check", "Add skeleton"
        ),
        encoding="utf-8",
        newline="",
    )

    code, output = run("fixtures", "--check", "--content-root", str(copied_library))

    assert code == 1
    assert "git/revert-a-pushed-commit" in output
    assert "practice fixtures --write" in output


def test_a_changed_fixture_names_the_commit_that_moved(copied_library: Path) -> None:
    """Editing c1's message changes c1 and therefore c2 and c3, because each
    commit's hash covers its parents. Seeing all three move is the signal that
    the edit was to the base of the history, which is exactly the kind of thing
    a one-line "out of date" message would hide.
    """
    fixture = copied_library / "git" / "revert-a-pushed-commit" / "fixture.sh"
    fixture.write_text(
        fixture.read_text(encoding="utf-8").replace(
            "Add project skeleton and build check", "Add skeleton"
        ),
        encoding="utf-8",
        newline="",
    )

    _, output = run("fixtures", "--check", "--content-root", str(copied_library))

    for alias in ("alias c1", "alias c2", "alias c3"):
        assert alias in output


def test_a_missing_lock_file_says_how_to_create_one(copied_library: Path) -> None:
    (copied_library / LOCK_FILENAME).unlink()

    code, output = run("fixtures", "--check", "--content-root", str(copied_library))

    assert code == 1
    assert "practice fixtures --write" in output


def test_write_then_check_agree(copied_library: Path) -> None:
    """Round-tripped through the real filesystem and real fixtures.

    Without this, `--write` could produce a file `--check` rejects, and the
    command would be unusable in the one workflow it exists for.
    """
    (copied_library / LOCK_FILENAME).unlink()

    write_code, _ = run("fixtures", "--write", "--content-root", str(copied_library))
    check_code, output = run(
        "fixtures", "--check", "--content-root", str(copied_library)
    )

    assert write_code == 0
    assert check_code == 0, output


def test_write_is_reproducible(copied_library: Path) -> None:
    """Writing twice must produce a byte-identical file, or every regeneration
    would show a spurious diff and the real ones would stop being noticed.
    """
    run("fixtures", "--write", "--content-root", str(copied_library))
    first = (copied_library / LOCK_FILENAME).read_bytes()
    run("fixtures", "--write", "--content-root", str(copied_library))

    assert (copied_library / LOCK_FILENAME).read_bytes() == first


def test_a_failing_fixture_is_reported_rather_than_locked(
    copied_library: Path,
) -> None:
    """A fixture that cannot run must not be recorded as having no commits,
    which would otherwise lock in a broken exercise as if it were fine.
    """
    fixture = copied_library / "git" / "revert-a-pushed-commit" / "fixture.sh"
    fixture.write_text("#!/usr/bin/env bash\nexit 7\n", encoding="utf-8", newline="")

    code, output = run("fixtures", "--write", "--content-root", str(copied_library))

    assert code == 1
    assert "a fixture failed" in output


# --- practice gc -----------------------------------------------------------


def test_gc_reports_nothing_before_anything_is_provisioned(tmp_path: Path) -> None:
    code, output = run("gc", "--workspace-root", str(tmp_path / "absent"))

    assert code == 0
    assert "nothing has been provisioned" in output


def test_gc_lists_a_provisioned_workspace(tmp_path: Path) -> None:
    workspace_root = tmp_path / "ws"
    provisioner = SubprocessSandboxProvisioner(
        content_root=content_root(), workspace_root=workspace_root
    )
    attempt_id = AttemptId.parse("3f2a1b0c-0000-4000-8000-000000000009")
    workspace = provisioner.provision(_flagship(), attempt_id)
    try:
        code, output = run("gc", "--workspace-root", str(workspace_root))

        assert code == 0
        assert attempt_id.short in output
        assert "git/revert-a-pushed-commit" in output
    finally:
        workspace.dispose()


def test_gc_says_it_deleted_nothing(tmp_path: Path) -> None:
    """The promise that makes it safe to run at this phase.

    An orphan is *a workspace with no active attempt row* (PLAN.md §8.1), and
    there is no attempt table until Phase 6 — so "collect orphans" would
    cheerfully delete the workspace of a session open in another tab.
    """
    workspace_root = tmp_path / "ws"
    provisioner = SubprocessSandboxProvisioner(
        content_root=content_root(), workspace_root=workspace_root
    )
    attempt_id = AttemptId.parse("3f2a1b0c-0000-4000-8000-000000000010")
    workspace = provisioner.provision(_flagship(), attempt_id)
    try:
        code, output = run("gc", "--workspace-root", str(workspace_root))

        assert code == 0
        assert "Nothing deleted" in output
        assert workspace.root.is_dir(), "gc must not have deleted it"
    finally:
        workspace.dispose()


def test_gc_refuses_to_delete(tmp_path: Path) -> None:
    """`--no-dry-run` is refused outright rather than quietly ignored.

    A flag that appears to enable deletion and does nothing is worse than one
    that is not offered: the next person to read the output would believe the
    cache had been cleared.
    """
    code, output = run("gc", "--no-dry-run", "--workspace-root", str(tmp_path))

    assert code == 2
    assert "phase 6" in output


def _flagship() -> Exercise:
    exercise = FilesystemContentRepository(content_root()).get(FLAGSHIP)
    assert exercise is not None
    return exercise
