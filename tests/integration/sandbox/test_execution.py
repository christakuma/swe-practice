"""Running one process: timeouts, process trees, output caps.

Driven through `run_process` directly rather than through a workspace, because
these are properties of the executor and tying them to whatever an exercise
happens to allow would make them fragile. `sleep` is used as the thing that
hangs: it is in Git for Windows' `usr/bin` and in `/usr/bin` on POSIX, both of
which the sandbox `PATH` already contains for the benefit of fixtures.
"""

from __future__ import annotations

import os
import shutil
import time
from typing import TYPE_CHECKING

import pytest

from practice.adapters.sandbox import run_process, sandbox_environment
from practice.adapters.sandbox.env import SandboxPaths, sandbox_path_entries
from practice.adapters.sandbox.execution import (
    NOT_FOUND_EXIT_CODE,
    TIMEOUT_EXIT_CODE,
    TRUNCATION_MARKER,
    resolve_program,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@pytest.fixture
def paths(tmp_path: Path) -> SandboxPaths:
    """A workspace-shaped directory, built here rather than by the provisioner.

    The executor does not know what a workspace is and these tests should not
    either: it takes a working directory and an environment. Assembling the
    paths by hand keeps that boundary visible, and keeps this file runnable
    without anything that provisions.
    """
    root = tmp_path / "ws"
    for directory in (root, root / "repo", root / "tmp"):
        directory.mkdir(parents=True)
    return SandboxPaths(
        home=root,
        repo=root / "repo",
        remotes=root / "remotes",
        tmp=root / "tmp",
        gitconfig=root / ".gitconfig",
        fixture_lib=root / "lib" / "fixture_lib.sh",
        aliases=root / "aliases",
        snapshot=root / "snapshot",
        clock=root / "clock",
    )


@pytest.fixture
def environment(paths: SandboxPaths) -> Mapping[str, str]:
    """The scoped environment, built from the installed git.

    No separate "is git present" fixture: `sandbox_path_entries` calls
    `find_git`, which raises `ToolNotFoundError` naming what to install, and it
    does so during fixture setup — so the failure is already both early and
    actionable.
    """
    return sandbox_environment(paths, path_entries=sandbox_path_entries())


# --- resolution ------------------------------------------------------------


def test_git_resolves_on_the_sandbox_path(environment: Mapping[str, str]) -> None:
    """The scoped `PATH` has to be able to find the tools fixtures need."""
    assert resolve_program("git", environment) is not None


def test_resolution_uses_the_sandbox_path_and_not_this_processs(
    environment: Mapping[str, str],
) -> None:
    """Otherwise the scoping in `sandbox_environment` is decorative.

    On Windows `subprocess` would search the *parent's* `PATH` for a bare name,
    which is the specific way this guarantee gets lost by accident.
    """
    narrowed = {**environment, "PATH": ""}

    assert resolve_program("git", narrowed) is None


def test_an_unresolvable_program_reports_127(
    paths: SandboxPaths, environment: Mapping[str, str]
) -> None:
    """The shell convention, produced here because there is no shell."""
    result = run_process(
        ["definitely-not-a-program"],
        cwd=paths.repo,
        environment=environment,
        timeout=5,
    )

    assert result.exit_code == NOT_FOUND_EXIT_CODE
    assert "command not found" in result.stderr


# --- exit codes and output -------------------------------------------------


def test_it_captures_stdout(
    paths: SandboxPaths, environment: Mapping[str, str]
) -> None:
    result = run_process(
        ["git", "--version"], cwd=paths.repo, environment=environment, timeout=10
    )

    assert result.succeeded
    assert result.stdout.startswith("git version")


def test_it_captures_a_failure(
    paths: SandboxPaths, environment: Mapping[str, str]
) -> None:
    """`git status` outside a repository, which is also the `GIT_CEILING_
    DIRECTORIES` guarantee: it must fail rather than find a repository above.
    """
    result = run_process(
        ["git", "status"], cwd=paths.home, environment=environment, timeout=10
    )

    assert not result.succeeded
    assert "not a git repository" in result.stderr.lower()


def test_output_is_capped_with_a_marker(
    paths: SandboxPaths, environment: Mapping[str, str]
) -> None:
    """64 KB per stream by default; a small limit here keeps the test quick."""
    result = run_process(
        ["git", "help", "-a"],
        cwd=paths.repo,
        environment=environment,
        timeout=20,
        output_limit=200,
    )

    assert result.truncated
    assert result.stdout.endswith(TRUNCATION_MARKER)
    assert len(result.stdout) < 200 + len(TRUNCATION_MARKER) + 1


def test_a_duration_is_recorded(
    paths: SandboxPaths, environment: Mapping[str, str]
) -> None:
    result = run_process(
        ["git", "--version"], cwd=paths.repo, environment=environment, timeout=10
    )

    assert result.duration_ms >= 0


# --- timeouts --------------------------------------------------------------


def test_a_hanging_command_is_killed(
    paths: SandboxPaths, environment: Mapping[str, str]
) -> None:
    """The timeout has to produce a readable result, not a hung application."""
    started = time.monotonic()
    result = run_process(
        ["sleep", "30"], cwd=paths.repo, environment=environment, timeout=1
    )
    elapsed = time.monotonic() - started

    assert result.timed_out
    assert result.exit_code == TIMEOUT_EXIT_CODE
    assert "Timed out after 1s" in result.stderr
    assert elapsed < 20, "the kill did not take effect"


def test_a_timed_out_command_does_not_leave_the_workspace_locked(
    paths: SandboxPaths, environment: Mapping[str, str]
) -> None:
    """The reason the tree kill matters on Windows specifically.

    A surviving grandchild holds file handles, and a workspace with an open
    handle in it cannot be deleted — so an incomplete kill turns one timed-out
    command into a workspace that `practice gc` reports forever and can never
    collect.
    """
    run_process(["sleep", "30"], cwd=paths.repo, environment=environment, timeout=1)

    shutil.rmtree(paths.home)

    assert not paths.home.exists()


@pytest.mark.skipif(
    os.name == "nt", reason="grandchildren need a shell to spawn portably"
)
def test_a_grandchild_is_killed_too(
    paths: SandboxPaths, environment: Mapping[str, str]
) -> None:
    """`subprocess.run(timeout=...)` kills the direct child only (PLAN.md §7).

    POSIX only, because the portable way to spawn a grandchild is a shell and
    the point of the sandbox is that user commands never get one. The Windows
    half of this is `taskkill /T`, exercised by the test above through the file
    handles a survivor would hold.
    """
    result = run_process(
        ["sh", "-c", "sleep 30 & sleep 30"],
        cwd=paths.repo,
        environment=environment,
        timeout=1,
    )

    assert result.timed_out
