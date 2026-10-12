"""A solver's progress never leaves their machine by way of this repository.

The repository is public and the attempt history is personal: which exercises
somebody has done, when, how many tries each took and what they typed. Two
separate things keep the second out of the first, and each is held here because
either one alone has a way round it.

**Where it lives.** `config.py` puts the database in the per-user data
directory and the workspaces in the per-user cache — outside the checkout, so
there is nothing in the working tree for `git add .` to pick up. That is the
real guarantee, and it is the first two tests.

**What git would do if it did not.** Both paths are overridable, by an
environment variable and by a flag, and "I'll just keep the database beside the
code" is a reasonable thing to type. `.gitignore` is what makes that harmless,
and the remaining tests ask git itself rather than reading the file: an ignore
rule that looks right and matches nothing is the failure this would otherwise
miss, and the control case is there so the question is seen to have a no.

What this does not cover, on purpose: a *workspace root* pointed at an arbitrary
directory inside the checkout. Only `/ws/` and `/workspaces/` are ignored, and
no pattern can recognise a workspace by what is in it. The default is the
protection there.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from practice import config
from practice.adapters.sandbox import run_process

if TYPE_CHECKING:
    from practice.adapters.sandbox import Execution

ROOT = config.project_root()

#: Long enough for a cold `git` on a loaded CI runner; the commands are instant.
TIMEOUT_SECONDS = 30.0


def git(*argv: str) -> Execution:
    return run_process(
        ["git", *argv],
        cwd=ROOT,
        environment=dict(os.environ),
        timeout=TIMEOUT_SECONDS,
    )


def is_ignored(path: str) -> bool:
    """`git check-ignore -q` exits 0 for an ignored path and 1 for one that is
    not. Anything else is git failing to answer, which must not read as a no.
    """
    result = git("check-ignore", "-q", path)
    assert result.exit_code in {0, 1}, result.stderr
    return result.exit_code == 0


# --- where it lives ------------------------------------------------------------


def test_the_database_is_kept_outside_the_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default, with the suite's own override taken away. Every test runs
    with `PRACTICE_DATABASE_PATH` set, so without the `delenv` this would be a
    statement about a temp directory.
    """
    monkeypatch.delenv(config.DATABASE_PATH_ENV, raising=False)

    assert not config.database_path().is_relative_to(ROOT)


def test_workspaces_are_kept_outside_the_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A workspace holds what the solver typed: their solution file, or the
    repository they were repairing.
    """
    monkeypatch.delenv(config.WORKSPACE_ROOT_ENV, raising=False)

    assert not config.workspace_root().is_relative_to(ROOT)


# --- what git would do if it did not --------------------------------------------


def test_the_question_can_be_answered_no() -> None:
    """The control. If `is_ignored` said yes to everything, every test below it
    would pass and prove nothing.
    """
    assert not is_ignored("src/practice/config.py")
    assert not is_ignored("content/tracks.yaml")


@pytest.mark.parametrize(
    "path",
    [
        # The database by its own name, at the root and anywhere below it.
        "practice.db",
        "data/practice.db",
        "src/practice/practice.db",
        # SQLite's two siblings. In WAL mode the newest attempts are in the
        # `-wal` file until a checkpoint, so ignoring only the main file would
        # leave exactly the most recent work unprotected.
        "practice.db-wal",
        "practice.db-shm",
        "data/practice.db-wal",
        # The same file under a name somebody chose, and a backup of it.
        "my-progress.db",
        "attempts.sqlite",
        "attempts.sqlite3",
        "practice.db.bak",
        # A workspace root made beside the code under the two obvious names.
        "ws/2464e198/workspace.json",
        "ws/2464e198/repo/solution.py",
        "workspaces/2464e198/repo/solution.py",
    ],
)
def test_git_ignores_progress_kept_inside_the_checkout(path: str) -> None:
    assert is_ignored(path), f"{path} would be picked up by `git add .`"


def test_nothing_that_looks_like_progress_is_tracked() -> None:
    """An ignore rule does nothing for a file that was committed before the
    rule existed, so the index is asked as well.
    """
    listed = git("ls-files")
    assert listed.exit_code == 0, listed.stderr

    suspicious = [
        path
        for path in listed.stdout.splitlines()
        if path.endswith(
            (".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", "/workspace.json")
        )
        or path.startswith(("ws/", "workspaces/"))
    ]

    assert suspicious == []
