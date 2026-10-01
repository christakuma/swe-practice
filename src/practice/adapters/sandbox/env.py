"""The environment every sandboxed process gets, and the clock that dates it.

**Built from nothing, not inherited.** `os.environ` is never copied. The whole
reproducibility claim in PLAN.md §6.1 is that a fixture behaves the same on this
machine as in CI, and the fastest way to lose it is a developer whose
environment holds `GIT_DIR`, a `pull.rebase` preference reachable through `HOME`,
or a `git` earlier on `PATH` than the one we resolved. So the mapping below is
assembled from an explicit list, and anything not on it is simply absent.

The cost of that choice is `PATH`, and it is worth being concrete about why.
Fixtures are bash scripts that call `git`, `mkdir` and `dirname`; on Windows all
three live inside the Git for Windows installation and none of them is on a
minimal `PATH`. So `PATH` is rebuilt from the *discovered* git location plus the
platform's own system directories — which is also the scoping that stops a
second git installation from deciding what a fixture does.

**Why the clock lives here.** Commit dates are environment variables, and
PLAN.md §6.1's hard-won detail is that the pinned clock has to span the whole
attempt rather than just the fixture: if it stops when the fixture does, any
commit the *solver* makes falls back to wall-clock time and the attempt stops
being reproducible. `SandboxClock` keeps its position in a file in the
workspace, so the sequence survives the process exiting — which is what lets a
resumed attempt continue the history rather than restart it.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

__all__ = [
    "FIXTURE_EPOCH",
    "FIXTURE_IDENTITY",
    "FIXTURE_STEP",
    "GitIdentity",
    "SandboxClock",
    "SandboxPaths",
    "ToolNotFoundError",
    "find_git",
    "git_install_root",
    "git_path_entries",
    "sandbox_environment",
    "sandbox_path_entries",
    "system_path_entries",
    "with_commit_date",
]

#: Where Git for Windows keeps the pieces a fixture needs: coreutils in
#: `usr/bin`, the real git in `mingw64/bin`, the wrapper in `cmd`. Also what
#: identifies an installation root, since a POSIX prefix has none of them.
_WINDOWS_GIT_SUBDIRS: Final = ("usr/bin", "mingw64/bin", "mingw32/bin", "cmd")

#: 2024-03-04T09:00:00Z. An arbitrary instant, fixed forever: every commit hash
#: in `content/fixtures.lock` depends on it, so changing it rewrites the lock.
FIXTURE_EPOCH: Final = 1709542800

#: Seven minutes between commits. Enough that `git log` reads as an afternoon of
#: work rather than ten commits at one instant, which matters because reading a
#: log is half of what these exercises teach.
FIXTURE_STEP: Final = 420


@dataclass(frozen=True, slots=True)
class GitIdentity:
    """Who a sandboxed commit is by.

    Pinned rather than taken from the solver's real git config, because the
    author and committer identities are both inputs to a commit hash — the same
    fixture committed as you would hash differently from the same fixture
    committed in CI (PLAN.md §6.1).
    """

    name: str
    email: str


#: The identity every fixture and every solver commit is made under. `.invalid`
#: is the reserved TLD from RFC 2606, so the address cannot ever resolve.
FIXTURE_IDENTITY: Final = GitIdentity(
    name="Practice Fixture",
    email="fixture@practice.invalid",
)


@dataclass(frozen=True, slots=True)
class SandboxPaths:
    """The directories and files a sandboxed process is told about.

    A value object rather than nine keyword arguments because the fixture
    runner, the workspace and the provisioner all need the same set, and three
    call sites assembling it by hand is three chances to forget `PRACTICE_CLOCK`
    and silently lose the clock continuation described above.
    """

    home: Path
    repo: Path
    remotes: Path
    tmp: Path
    gitconfig: Path
    fixture_lib: Path
    aliases: Path
    snapshot: Path
    clock: Path


class ToolNotFoundError(Exception):
    """git or the bash it bundles could not be located.

    Raised rather than skipped past. A sandbox that silently degraded when git
    was missing would report a fixture as having built nothing, which is the
    same shape as a fixture that built nothing — so the message names what to
    install instead.
    """


@lru_cache(maxsize=1)
def find_git() -> Path:
    """The `git` this process will use, resolved once.

    Cached because it is looked up per command and the answer cannot change
    inside one run. The lookup is against the *ambient* `PATH`, not the sandbox
    one: this is the question "which git is installed", and the sandbox `PATH`
    is then built from the answer.
    """
    found = shutil.which("git")
    if found is None:
        raise ToolNotFoundError(
            "git is not on PATH. The sandbox runs real git against real "
            "repositories, so there is nothing to fall back to; install git "
            "2.32 or newer."
        )
    return Path(found).resolve()


@lru_cache(maxsize=1)
def git_install_root() -> Path | None:
    """The root of the git installation, or `None` if it is a POSIX prefix.

    Git for Windows puts the real binary at `<root>/mingw64/bin/git.exe` and a
    wrapper at `<root>/cmd/git.exe`, with coreutils in `<root>/usr/bin` and bash
    beside them. So the root is the nearest ancestor of the git executable that
    contains one of those subdirectories — found by looking rather than by
    counting `parents[n]`, because the depth differs between the two places git
    can be invoked from.

    `None` on a POSIX install, where there is no bundle: git is in `/usr/bin`
    with everything else, and `/usr/bin` is not an installation root.
    """
    git = find_git()
    for parent in git.parents:
        if any((parent / subdir).is_dir() for subdir in _WINDOWS_GIT_SUBDIRS):
            return parent
    return None


def git_path_entries() -> tuple[str, ...]:
    """The `PATH` entries that make git and coreutils reachable.

    The part of the scoped `PATH` that cannot be a constant. On Windows these
    are the directories inside the Git for Windows installation, because a
    fixture calling `dirname` and `mkdir` finds nothing without them — proven by
    running one, which failed with `git: command not found`. On POSIX it is
    wherever git itself lives, which may be a package manager prefix rather than
    `/usr/bin`.
    """
    root = git_install_root()
    if root is None:
        return (str(find_git().parent),)
    return tuple(
        str(root / subdir)
        for subdir in _WINDOWS_GIT_SUBDIRS
        if (root / subdir).is_dir()
    )


def system_path_entries() -> tuple[str, ...]:
    """The platform's own directories, for a `PATH` built from scratch.

    Deliberately not the user's `PATH`: the point of the scoped environment is
    that what is on it is ours. These entries are needed on Windows because Git
    for Windows shells out to `cmd` in places, and on POSIX because coreutils
    live there and fixtures call them.
    """
    if os.name == "nt":
        system_root = os.environ.get("SYSTEMROOT") or r"C:\Windows"
        root = Path(system_root)
        return (str(root / "System32"), str(root), str(root / "System32" / "Wbem"))
    return ("/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin")


#: Ambient variables passed through on Windows. Git for Windows and the MSYS
#: runtime both read them, and a process started without `SYSTEMROOT` fails in
#: ways that look nothing like the cause. `TEMP` and `TMP` are absent on
#: purpose — they are overridden to the workspace, not inherited.
_WINDOWS_PASSTHROUGH: Final = (
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "NUMBER_OF_PROCESSORS",
)


def sandbox_path_entries() -> tuple[str, ...]:
    """The whole scoped `PATH`: the git installation, then the platform.

    Here rather than left to the caller because every caller wants the same
    thing in the same order, and the order matters — git's own coreutils must
    win over anything the platform ships under the same name.
    """
    return (*git_path_entries(), *system_path_entries())


def sandbox_environment(
    paths: SandboxPaths,
    *,
    path_entries: Iterable[str],
    identity: GitIdentity = FIXTURE_IDENTITY,
) -> dict[str, str]:
    """The full environment for a fixture or a solver command.

    Every entry is either load-bearing for reproducibility or load-bearing for
    not hanging. The ones worth reading twice:

    * `HOME` and `USERPROFILE` point at the workspace, so nothing can reach the
      developer's real git config by a back door `GIT_CONFIG_GLOBAL` does not
      cover.
    * `GIT_EDITOR=false` and `GIT_SEQUENCE_EDITOR=false` turn `git commit` with
      no `-m` into an immediate, readable failure. Without them it launches an
      editor, finds no terminal, and hangs until the timeout expires — a ten
      second stall with no explanation, which PLAN.md §8.1 notes you would hit
      within five minutes of using the tool.
    * `GIT_CEILING_DIRECTORIES` stops repository discovery walking out of the
      workspace. A command run somewhere that is not a repository should say so,
      not quietly operate on whatever repository happens to be above it.
    * `LC_ALL=C` fixes git's own messages in one language. The reflog and
      porcelain parsing downstream reads them, and so does the solver.
    """
    environment = {
        "PATH": os.pathsep.join(path_entries),
        # The scoped home, under both names: Git for Windows falls back to
        # USERPROFILE when HOME is unset, and this does not rely on which.
        "HOME": str(paths.home),
        "USERPROFILE": str(paths.home),
        "TMPDIR": str(paths.tmp),
        "TEMP": str(paths.tmp),
        "TMP": str(paths.tmp),
        "GIT_CONFIG_GLOBAL": str(paths.gitconfig),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CEILING_DIRECTORIES": str(paths.home),
        # No network, ever: every remote is a bare repository inside the
        # workspace, so a credential prompt could only ever be a hang.
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_EDITOR": "false",
        "GIT_SEQUENCE_EDITOR": "false",
        "GIT_PAGER": "cat",
        "GIT_AUTHOR_NAME": identity.name,
        "GIT_AUTHOR_EMAIL": identity.email,
        "GIT_COMMITTER_NAME": identity.name,
        "GIT_COMMITTER_EMAIL": identity.email,
        "LC_ALL": "C",
        "TERM": "dumb",
        # The fixture contract (content/_lib/fixture_lib.sh). Posix paths,
        # because the consumer is bash — including on Windows.
        "PRACTICE_FIXTURE_LIB": paths.fixture_lib.as_posix(),
        "PRACTICE_ALIASES": paths.aliases.as_posix(),
        "PRACTICE_SNAPSHOT": paths.snapshot.as_posix(),
        "PRACTICE_REMOTES": paths.remotes.as_posix(),
        "PRACTICE_CLOCK": paths.clock.as_posix(),
        "PRACTICE_EPOCH": str(FIXTURE_EPOCH),
        "PRACTICE_STEP": str(FIXTURE_STEP),
    }
    if os.name == "nt":
        for name in _WINDOWS_PASSTHROUGH:
            value = os.environ.get(name)
            if value:
                environment[name] = value
    return environment


def with_commit_date(environment: Mapping[str, str], epoch: int) -> dict[str, str]:
    """A copy of `environment` with both commit dates pinned to `epoch`.

    `@<epoch> +0000` is a format git accepts directly, which sidesteps every
    portability problem with formatting a date in a shell or trusting the local
    timezone to be what it was yesterday.
    """
    stamp = f"@{epoch} +0000"
    return {**environment, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}


class SandboxClock:
    """The fixture's clock, continued into the attempt.

    Backed by a file in the workspace rather than by an attribute, for one
    reason: the fixture advances it inside a bash process that then exits, and a
    resumed attempt advances it in a Python process that did not provision the
    workspace. Neither can tell the other where the clock got to except through
    the workspace itself.
    """

    __slots__ = ("_epoch", "_path", "_step")

    def __init__(
        self,
        path: Path,
        *,
        epoch: int = FIXTURE_EPOCH,
        step: int = FIXTURE_STEP,
    ) -> None:
        self._path = path
        self._epoch = epoch
        self._step = step

    @property
    def path(self) -> Path:
        return self._path

    def start(self) -> None:
        """Set the clock to its initial position, before any fixture runs."""
        self._write(self._epoch)

    def read(self) -> int:
        """The epoch of the most recent commit, or the start if there is none.

        Unreadable or corrupt content falls back to the start rather than
        raising. A clock file someone has edited by hand is a reproducibility
        problem, not a reason to refuse to run the attempt — and the fallback is
        the value the fixture would have begun from anyway.
        """
        try:
            return int(self._path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return self._epoch

    def tick(self) -> int:
        """Advance one step and return the new position."""
        advanced = self.read() + self._step
        self._write(advanced)
        return advanced

    def _write(self, epoch: int) -> None:
        self._path.write_text(f"{epoch}\n", encoding="utf-8")
