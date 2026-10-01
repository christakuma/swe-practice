"""Finding git and bash, running a fixture, and recording what it built.

Fixtures are **trusted** code — you author them — so they get a real shell, with
the pinned environment from PLAN.md §6.1 around them. What this module adds on
top of "run a bash script" is the two records the check engine needs afterwards:
the alias map the fixture appended to, and a snapshot of every ref as the
fixture left it.

**Bash discovery is the one genuinely platform-specific thing in the project,
and `shutil.which("bash")` is the wrong answer on Windows.** On this machine it
returns three candidates in this order:

    C:\\Program Files\\Git\\usr\\bin\\bash.exe      <- the one we want
    C:\\Windows\\System32\\bash.exe                 <- WSL
    C:\\Users\\...\\WindowsApps\\bash.exe           <- the Store stub for WSL

Only the first can run a fixture. The second starts a Linux distribution with a
different filesystem, where the workspace path does not exist; the third may
only exist to open the Store. `which` is also sensitive to `PATH` order, and the
System32 entry is on every Windows `PATH` by default. So bash is located by
walking up from the resolved `git` executable to the installation root and
looking for the bash *bundled with it* — which also guarantees the bash and the
git are the same installation.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Final

from practice.adapters.sandbox.env import (
    ToolNotFoundError,
    find_git,
    git_install_root,
    with_commit_date,
)
from practice.adapters.sandbox.execution import run_process
from practice.adapters.sandbox.workspace import read_sha_map

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.adapters.sandbox.execution import Execution
    from practice.adapters.sandbox.workspace import WorkspaceLayout
    from practice.domain.ids import Sha

__all__ = [
    "FIXTURE_TIMEOUT_SECONDS",
    "FixtureError",
    "FixtureResult",
    "find_bash",
    "run_fixture",
]

#: Fixtures are a dozen git commands against an empty repository. A minute is
#: far more than any of them needs, and short enough that a fixture which hangs
#: — `git commit` with no message and no `GIT_EDITOR`, say — fails a test run
#: rather than stalling it.
FIXTURE_TIMEOUT_SECONDS: Final = 60.0

#: Candidate locations of the bundled bash, relative to the installation root,
#: in preference order. Git for Windows uses `usr/bin`; a POSIX prefix install
#: uses `bin`.
_BASH_CANDIDATES: Final = (
    "usr/bin/bash.exe",
    "bin/bash.exe",
    "usr/bin/bash",
    "bin/bash",
)


@lru_cache(maxsize=1)
def find_bash() -> Path:
    """The bash that ships with the installed git.

    Anchored on `git_install_root` rather than on a `PATH` search, for the
    reason in the module docstring. Falls back to the system bash only on POSIX,
    where there is no bundle and `/bin/bash` is the same bash anyway — never on
    Windows, where the fallback would be WSL.
    """
    root = git_install_root()
    if root is not None:
        for candidate in _BASH_CANDIDATES:
            path = root / candidate
            if path.is_file():
                return path

    if os.name != "nt":
        found = shutil.which("bash")
        if found is not None:
            return Path(found).resolve()

    raise ToolNotFoundError(
        f"no bash found alongside {find_git()}. Fixtures are bash scripts, so "
        f"one is required; on Windows install Git for Windows, which bundles "
        f"it. Note that WSL's bash cannot be used: it runs in a different "
        f"filesystem and cannot see the workspace."
    )


class FixtureError(Exception):
    """A fixture did not complete. Carries its output, because that is the bug.

    The workspace is deliberately *not* disposed of when this is raised: a
    fixture that failed halfway is the only evidence of why, and `root` says
    where to go and look.
    """

    def __init__(self, fixture: Path, root: Path, execution: Execution) -> None:
        self.fixture = fixture
        self.root = root
        self.execution = execution
        detail = (execution.stderr or execution.stdout or "").strip()
        super().__init__(
            f"{fixture.name} exited {execution.exit_code}; workspace kept at "
            f"{root}\n{detail}"
        )


@dataclass(frozen=True, slots=True)
class FixtureResult:
    """What a fixture left behind."""

    aliases: Mapping[str, Sha]
    refs: Mapping[str, Sha]
    execution: Execution


def run_fixture(
    layout: WorkspaceLayout,
    *,
    environment: Mapping[str, str],
    timeout: float = FIXTURE_TIMEOUT_SECONDS,
) -> FixtureResult:
    """Run the workspace's fixture, then record the aliases and the refs.

    `--noprofile --norc` is not belt and braces. Git Bash reads `/etc/profile`,
    which rewrites `PATH` to the MSYS default and would undo the scoped `PATH`
    assembled above; and a developer with a `~/.bashrc` would get a different
    fixture run from CI, which is the whole thing we are trying to prevent.
    """
    fixture = layout.fixture
    execution = run_process(
        [str(find_bash()), "--noprofile", "--norc", fixture.as_posix()],
        cwd=layout.repo,
        environment=with_commit_date(environment, _starting_epoch(environment)),
        timeout=timeout,
    )
    if not execution.succeeded:
        raise FixtureError(fixture, layout.root, execution)

    refs = _snapshot_refs(layout, environment=environment)
    return FixtureResult(
        aliases=read_sha_map(layout.aliases, separator="="),
        refs=refs,
        execution=execution,
    )


def _starting_epoch(environment: Mapping[str, str]) -> int:
    """The clock the fixture inherits before `commit_as` advances it.

    A fixture that commits without `commit_as` — plain `git commit` — would
    otherwise get wall-clock dates and break the lock file, so the dates are set
    before bash starts rather than only inside the helper.
    """
    return int(environment["PRACTICE_EPOCH"])


def _snapshot_refs(
    layout: WorkspaceLayout, *, environment: Mapping[str, str]
) -> Mapping[str, Sha]:
    """Record every ref and `HEAD`, which is what `ref_unchanged` compares to.

    `HEAD` is included even though it is not a ref `for-each-ref` reports,
    because an exercise asking whether the solver ended up back on a branch
    needs to know where HEAD started.
    """
    refs = _git(
        layout, environment, "for-each-ref", "--format=%(refname) %(objectname)"
    )
    head = _git(layout, environment, "rev-parse", "HEAD").strip()
    lines = [line for line in refs.splitlines() if line.strip()]
    if head:
        lines.append(f"HEAD {head}")
    layout.snapshot.write_text(
        "".join(f"{line}\n" for line in sorted(lines)), encoding="utf-8"
    )
    return read_sha_map(layout.snapshot)


def _git(
    layout: WorkspaceLayout, environment: Mapping[str, str], *arguments: str
) -> str:
    """One read-only git command for the snapshot. Failures yield no output.

    Tolerant on purpose: a fixture is allowed to leave a repository with no
    commits — one that only sets up a working directory, say — and
    `rev-parse HEAD` failing there is an empty snapshot, not an error.
    """
    execution = run_process(
        ["git", *arguments],
        cwd=layout.repo,
        environment=environment,
        timeout=FIXTURE_TIMEOUT_SECONDS,
    )
    return execution.stdout if execution.succeeded else ""
