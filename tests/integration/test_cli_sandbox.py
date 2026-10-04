"""`practice fixtures` and `practice gc`, driven through Typer's runner.

Integration rather than unit for the reason the `validate` suite gives: the
whole job of both commands is to read what is on disk and say what is there, and
the exit code is the contract CI depends on. A test that stubbed the filesystem
would verify neither.

**This was the slowest file in the project and the reason is worth recording.**
Every `fixtures` invocation runs every git scenario's fixture, and the tests that
needed a library they could break copied the *whole* shipped one. At two
scenarios that cost a couple of seconds; at twenty-four it cost 288 seconds
across nine tests — 27% of the entire suite, spent fingerprinting the same
library nine times (§16).

So the tests that break a library now work on a **two-exercise subset**, built
once per session and copied per test. They are still real exercises, which was
the point of copying rather than hand-building: what is dropped is twenty-two
*repetitions* of the same evidence, not the evidence. The two tests that must
see the shipped library share one invocation of it.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest
import yaml
from typer.testing import CliRunner

from practice.adapters.content import FilesystemContentRepository
from practice.adapters.sandbox import SubprocessSandboxProvisioner
from practice.adapters.sandbox.fixture_lock import (
    LOCK_FILENAME,
    fingerprint_library,
    lock_path,
    render,
)
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


#: The exercises a breakable library is built from. Two, and both chosen:
#: `revert-a-pushed-commit` is the flagship whose three aliases the
#: commit-moved test asserts on, and a second one is needed so that "it named
#: every exercise it checked" is a claim about more than one.
SUBSET = ("git/revert-a-pushed-commit", "git/recover-a-lost-commit")


@pytest.fixture(scope="session")
def subset_library(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Two real exercises and a lock file, built once for the whole session.

    The lock is generated rather than copied-and-trimmed: `render` over a fresh
    fingerprint is two fixture runs and cannot disagree with what `--check` is
    about to compute, where editing the shipped lock file by hand could.

    Session-scoped and never mutated — `copied_library` hands out copies. That
    is what makes this two fixture runs for the file rather than two per test.
    """
    root = tmp_path_factory.mktemp("subset-content")
    shutil.copytree(content_root() / "_lib", root / "_lib")
    for exercise_id in SUBSET:
        shutil.copytree(content_root() / exercise_id, root / exercise_id)

    (root / "curriculum.yaml").write_text(
        yaml.safe_dump(
            {
                "tracks": [
                    {
                        "name": "subset",
                        "title": "The two exercises these tests run on",
                        "exercises": list(SUBSET),
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    exercises = FilesystemContentRepository(root).list_exercises()
    lock_path(root).write_text(
        render(fingerprint_library(exercises, content_root=root)),
        encoding="utf-8",
        newline="",
    )
    return root


@pytest.fixture
def copied_library(subset_library: Path, tmp_path: Path) -> Path:
    """A disposable copy of the subset, for a test that breaks something.

    A copy of real exercises rather than a synthetic library, because what these
    tests are about is the real thing: a hand-built exercise would prove the
    command works on hand-built exercises.
    """
    destination = tmp_path / "content"
    shutil.copytree(subset_library, destination)
    return destination


# --- practice fixtures -----------------------------------------------------


@pytest.fixture(scope="module")
def shipped_check() -> tuple[int, str]:
    """`fixtures --check` against the real library, run once for this module.

    The one invocation here that has to see all twenty-four fixtures, and the
    most expensive single thing in the suite at about thirty seconds. Two tests
    make two different claims about it, so it is a fixture rather than being
    inlined into one of them — granularity in the report without paying for it
    twice.
    """
    return run("fixtures", "--check")


def test_the_shipped_fixtures_match_the_lock_file(
    shipped_check: tuple[int, str],
) -> None:
    """The Phase 3 exit criterion, as far as one machine can take it.

    The other half is CI running this same command on the other platform. That
    is the whole design: the lock file is the shared reference, so a
    disagreement names which platform diverged instead of just going red.
    """
    code, output = shipped_check

    assert code == 0, output
    assert f"match {LOCK_FILENAME}" in output


def test_it_names_every_exercise_it_checked(shipped_check: tuple[int, str]) -> None:
    """A run that fingerprinted nothing would exit zero just as happily.

    The same hole `test_the_library_was_found` guards in the content suite, and
    the reason this asserts on names rather than on the exit code.
    """
    _, output = shipped_check

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


def test_gc_says_what_it_would_delete_without_deleting_it(tmp_path: Path) -> None:
    """`--dry-run` is still the default, and still the thing that makes gc safe to
    run without thinking about it.

    This workspace was provisioned through the provisioner directly, so there is no
    attempt row behind it and it *is* an orphan by PLAN.md §8.1's definition — which
    is what makes the assertion meaningful rather than vacuous.
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
        assert "re-run with --no-dry-run" in output
        assert workspace.root.is_dir(), "a dry run must not have deleted it"
    finally:
        workspace.dispose()


def test_gc_collects_an_orphan_when_it_is_asked_to(tmp_path: Path) -> None:
    """The half that could not exist before the attempt table.

    A real provisioned scenario workspace, which is the only version of this worth
    running here: it is full of loose git objects that git has marked read-only, and
    deleting one on Windows is the papercut `WorkspaceLayout.destroy` exists to
    absorb. A unit test against a fake provisioner cannot find that.
    """
    workspace_root = tmp_path / "ws"
    provisioner = SubprocessSandboxProvisioner(
        content_root=content_root(), workspace_root=workspace_root
    )
    attempt_id = AttemptId.parse("3f2a1b0c-0000-4000-8000-000000000011")
    workspace = provisioner.provision(_flagship(), attempt_id)

    code, output = run("gc", "--no-dry-run", "--workspace-root", str(workspace_root))

    assert code == 0
    assert "collected 1 workspace" in output
    assert not workspace.root.exists()


def _flagship() -> Exercise:
    exercise = FilesystemContentRepository(content_root()).get(FLAGSHIP)
    assert exercise is not None
    return exercise
