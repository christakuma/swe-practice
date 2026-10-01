"""The workspace, against real git in a real directory.

The tests that cannot be faked. Everything here is either about the shape of a
provisioned directory, about what a real `git` process sees when it runs inside
it, or about one of the Windows behaviours PLAN.md §8.1 budgets six sessions for.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from practice.adapters.sandbox import CommandRejectedError, WorkspacePathError
from practice.adapters.sandbox.execution import TIMEOUT_EXIT_CODE

if TYPE_CHECKING:
    from practice.adapters.sandbox import (
        SubprocessSandboxProvisioner,
        SubprocessWorkspace,
    )
    from practice.domain.exercise import Exercise
    from practice.domain.ids import AttemptId


# --- the shape of a workspace ----------------------------------------------


def test_the_repository_is_a_subdirectory(workspace: SubprocessWorkspace) -> None:
    """Not the workspace root, and the reason is `worktree_clean`.

    The alias map, the snapshot, the clock and the bare remotes all live in the
    workspace. If the repository were the root, every one of them would be an
    untracked file — `worktree_clean {include_untracked: true}` could never
    pass, and the state panel would be full of plumbing.
    """
    assert workspace.repo.is_dir()
    assert workspace.repo.parent == workspace.root
    assert (workspace.repo / ".git").is_dir()


def test_the_plumbing_is_invisible_to_git(workspace: SubprocessWorkspace) -> None:
    """The point of the layout above, asserted through git itself."""
    result = workspace.run(["git", "status", "--porcelain"], timeout=10)

    assert result.stdout == ""


def test_the_workspace_directory_is_named_after_the_attempt(
    workspace: SubprocessWorkspace, attempt_id: AttemptId
) -> None:
    """Short on purpose: `MAX_PATH` is 260 characters (PLAN.md §8.1)."""
    assert workspace.root.name == attempt_id.short
    assert len(workspace.root.name) == 8


def test_remotes_are_local_bare_repositories(workspace: SubprocessWorkspace) -> None:
    """There is no network, ever. A `remote` is a directory in the workspace."""
    assert (workspace.layout.remotes / "origin.git").is_dir()

    result = workspace.run(["git", "remote", "-v"], timeout=10)

    assert "origin" in result.stdout
    assert "http" not in result.stdout


# --- the scoped environment, as git sees it --------------------------------


def test_git_cannot_see_the_developers_config(
    workspace: SubprocessWorkspace,
) -> None:
    """The guarantee that makes a fixture behave the same here and in CI.

    Asserted through `git config --show-origin` rather than through the
    environment dictionary, because the dictionary is already unit-tested and
    what matters here is that git *honoured* it.

    The origin is matched on the workspace directory name rather than on the
    full path: on Windows, `--show-origin` prints the path quoted and with every
    backslash escaped, so comparing against `str(Path)` fails for a reason that
    has nothing to do with the guarantee.
    """
    result = workspace.run(
        ["git", "config", "--show-origin", "--get", "user.email"], timeout=10
    )

    assert "fixture@practice.invalid" in result.stdout
    assert workspace.root.name in result.stdout
    assert ".gitconfig" in result.stdout


def test_the_pinned_settings_are_in_effect(workspace: SubprocessWorkspace) -> None:
    """The four from the PLAN.md §6.1 table, read back out of git."""
    for setting, expected in (
        ("core.filemode", "false"),
        ("core.autocrlf", "false"),
        ("core.eol", "lf"),
        ("init.defaultbranch", "main"),
    ):
        result = workspace.run(["git", "config", "--get", setting], timeout=10)

        assert result.stdout.strip() == expected, setting


def test_garbage_collection_is_disabled(workspace: SubprocessWorkspace) -> None:
    """`recover-a-lost-commit` recovers commits no ref points at.

    Git starts a background gc on its own once enough loose objects accumulate,
    and gc is entitled to delete exactly those objects — which would make that
    exercise unsolvable for reasons nobody could reproduce.
    """
    for setting in ("gc.auto", "gc.reflogexpireunreachable"):
        result = workspace.run(["git", "config", "--get", setting], timeout=10)

        assert result.stdout.strip() in {"0", "never"}, setting


def test_a_commit_with_no_message_fails_instead_of_hanging(
    workspace: SubprocessWorkspace,
) -> None:
    """The ten-second stall PLAN.md §8.1 says you would hit in five minutes.

    Without `GIT_EDITOR=false`, `git commit` with no `-m` launches an editor,
    finds no terminal, and waits until the timeout. This test would take ten
    seconds and report a timeout rather than a failure, which is the signal that
    the setting has gone.
    """
    workspace.run(["write", "notes.md", "something"], timeout=10)
    workspace.run(["git", "add", "notes.md"], timeout=10)

    result = workspace.run(["git", "commit"], timeout=10)

    assert not result.succeeded
    assert result.exit_code != TIMEOUT_EXIT_CODE


def test_output_has_no_carriage_returns(workspace: SubprocessWorkspace) -> None:
    """So output captured on Windows compares equal to output captured on Linux.

    Which matters the moment a test, or a check, looks at it.
    """
    result = workspace.run(["git", "log", "--oneline"], timeout=10)

    assert "\r" not in result.stdout


def test_commits_are_dated_by_the_sandbox_clock(
    workspace: SubprocessWorkspace,
) -> None:
    """The clock spans the whole attempt, not just the fixture (PLAN.md §6.1).

    A commit the *solver* makes has to be deterministic too — otherwise
    reproducing a bug report, or storing a golden end state, is impossible.
    """
    workspace.run(["write", "notes.md", "a note"], timeout=10)
    workspace.run(["git", "add", "notes.md"], timeout=10)
    workspace.run(["git", "commit", "-m", "Add a note"], timeout=10)
    # Read before the next command: the clock advances on every command, not
    # only on the ones that commit, so asking it afterwards gets the tick that
    # the verifying `git log` consumed.
    at_commit = workspace.layout.clock.read_text().strip()

    result = workspace.run(["git", "log", "-1", "--format=%at"], timeout=10)

    assert result.stdout.strip() == at_commit


def test_the_clock_only_ever_moves_forward(workspace: SubprocessWorkspace) -> None:
    """So `git log` ordering stays sensible instead of stacking commits."""
    before = int(workspace.layout.clock.read_text().strip())
    workspace.run(["git", "status"], timeout=10)
    after = int(workspace.layout.clock.read_text().strip())

    assert after > before


# --- policy ----------------------------------------------------------------


def test_a_disallowed_command_never_runs(workspace: SubprocessWorkspace) -> None:
    """The workspace enforces the allowlist even though its caller already did.

    The same deliberate duplication `Attempt.record_command` documents: the use
    case refuses to offer a disallowed command, the aggregate refuses to
    remember one, and this refuses to execute one. A future code path that
    forgets the gate gets a readable rejection rather than an exercise whose
    allowlist quietly did not apply.
    """
    with pytest.raises(CommandRejectedError):
        workspace.run(["curl", "https://example.invalid"], timeout=10)


def test_an_allowed_virtual_command_runs(workspace: SubprocessWorkspace) -> None:
    """`write` is on this exercise's allowlist and has no executable anywhere."""
    result = workspace.run(["write", "scratch.txt", "hello"], timeout=10)

    assert result.succeeded
    assert (workspace.repo / "scratch.txt").read_text(encoding="utf-8") == "hello\n"


def test_a_virtual_command_and_a_real_one_agree_about_the_repository(
    workspace: SubprocessWorkspace,
) -> None:
    """`write` then `git add` has to see the same file, which is the whole
    reason virtual commands resolve against the repository and not the
    workspace.
    """
    workspace.run(["write", "scratch.txt", "hello"], timeout=10)

    result = workspace.run(["git", "status", "--porcelain"], timeout=10)

    assert "scratch.txt" in result.stdout


# --- files -----------------------------------------------------------------


def test_read_file_reads_from_the_repository(workspace: SubprocessWorkspace) -> None:
    assert "def parse" in workspace.read_file("parser.py")


def test_write_file_writes_lf(workspace: SubprocessWorkspace) -> None:
    """Python would write CRLF on Windows, changing the blob and every hash
    downstream of it — the `core.autocrlf` problem reintroduced by our own tool.
    """
    workspace.write_file("notes.md", "one\ntwo\n")

    assert b"\r" not in (workspace.repo / "notes.md").read_bytes()


def test_write_file_creates_missing_directories(
    workspace: SubprocessWorkspace,
) -> None:
    workspace.write_file("docs/notes.md", "hello\n")

    assert (workspace.repo / "docs" / "notes.md").is_file()


def test_a_path_outside_the_repository_is_refused(
    workspace: SubprocessWorkspace,
) -> None:
    with pytest.raises(WorkspacePathError):
        workspace.write_file("../escaped.txt", "x")

    assert not (workspace.root / "escaped.txt").exists()


def test_an_absolute_path_is_refused(workspace: SubprocessWorkspace) -> None:
    with pytest.raises(WorkspacePathError):
        workspace.read_file(str(workspace.layout.gitconfig))


# --- disposal, which is where Windows breaks -------------------------------


def test_disposal_removes_everything(
    provisioner: SubprocessSandboxProvisioner,
    flagship: Exercise,
    attempt_id: AttemptId,
) -> None:
    """The papercut this whole phase budgets for, as a test.

    `shutil.rmtree` fails on Windows with `WinError 5` on a loose git object:
    git marks them read-only and Windows honours that against deletion. Proven
    by running it before the handler existed, on
    `objects/0b/2626fa...` — which is c2's tree, so the first workspace that
    ever held a commit was already enough to hit it.
    """
    workspace = provisioner.provision(flagship, attempt_id)
    root = workspace.root
    assert any(root.rglob("objects/*/*")), "expected loose objects to exist"

    workspace.dispose()

    assert not root.exists()


def test_disposal_is_safe_to_call_twice(
    provisioner: SubprocessSandboxProvisioner,
    flagship: Exercise,
    attempt_id: AttemptId,
) -> None:
    """Because the use case disposes on submit and on abandon, and a crash
    between them should not turn cleanup into a second error.
    """
    workspace = provisioner.provision(flagship, attempt_id)
    workspace.dispose()
    workspace.dispose()

    assert not workspace.root.exists()


@pytest.mark.skipif(os.name != "nt", reason="read-only deletion is a Windows rule")
def test_disposal_clears_the_read_only_bit(workspace: SubprocessWorkspace) -> None:
    """Named separately from the test above so a failure says which rule broke."""
    objects = sorted(workspace.repo.rglob(".git/objects/*/*"))
    assert objects, "expected loose objects to exist"

    workspace.dispose()

    assert not workspace.root.exists()
