"""Finding git, and building the PATH a fixture needs.

Integration tests: these functions look at the filesystem, which is the whole
job. The bash half of discovery is tested alongside the fixture runner that
needs it.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from practice.adapters.sandbox.env import (
    ToolNotFoundError,
    find_git,
    git_install_root,
    git_path_entries,
    sandbox_path_entries,
    system_path_entries,
)


def test_git_is_found() -> None:
    assert find_git().is_file()


@pytest.mark.skipif(os.name != "nt", reason="only Windows has an install root")
def test_the_install_root_is_found_by_looking_not_counting() -> None:
    """git is at `<root>/mingw64/bin/git.exe` or `<root>/cmd/git.exe` depending
    on which one `PATH` resolves to, so the depth differs and `parents[n]` is
    the wrong tool. An earlier version used `parents[1]` and found `<root>/usr`,
    which produced a PATH with no git on it at all.
    """
    root = git_install_root()

    assert root is not None
    assert (root / "usr" / "bin").is_dir()


def test_the_path_can_find_the_tools_a_fixture_calls() -> None:
    """A fixture is a bash script calling `git`, `mkdir` and `dirname`. On
    Windows all three live inside the git installation and none is on a minimal
    PATH — proven by running one, which failed with `git: command not found`.
    """
    path = os.pathsep.join(sandbox_path_entries())

    for program in ("git", "mkdir", "dirname"):
        assert shutil.which(program, path=path) is not None, program


def test_the_git_entries_come_before_the_platforms() -> None:
    """Order matters: git's own coreutils must win over anything the platform
    ships under the same name, or a fixture gets a `mkdir` that was never tested
    with it.
    """
    entries = sandbox_path_entries()
    first_system = entries.index(system_path_entries()[0])

    assert all(entries.index(entry) < first_system for entry in git_path_entries())


def test_a_missing_tool_names_what_to_install() -> None:
    """The error has to be actionable, because the suite fails rather than skips
    when git is absent — a loud failure that does not say what to do is only
    half an improvement on a silent skip.
    """
    message = str(
        ToolNotFoundError(
            "git is not on PATH. The sandbox runs real git against real "
            "repositories, so there is nothing to fall back to; install git "
            "2.32 or newer."
        )
    )

    assert "install git" in message


def test_discovery_is_cached() -> None:
    """Looked up per command, and the answer cannot change inside one run."""
    assert find_git() is find_git()


def test_the_resolved_git_is_absolute() -> None:
    """So `Popen` never has to search a PATH of its own choosing."""
    assert Path(find_git()).is_absolute()
