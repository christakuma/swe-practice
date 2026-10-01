"""The directory an attempt lives in, and the thing that runs commands in it.

Two types, split by lifetime. `WorkspaceLayout` is just names — it can describe
a workspace that does not exist yet, which is what the provisioner needs while
it is building one and what `practice gc` needs while it is reading one it did
not create. `SubprocessWorkspace` is the live object that satisfies the
`Workspace` port.

**Why the repository is a subdirectory.** The workspace holds things the solver
must not see in `git status`: the alias map, the ref snapshot, the clock, the
bare remotes, the pinned gitconfig. If the repository were the workspace root,
every one of them would be an untracked file, `worktree_clean` would be
unfailable in its `include_untracked` form, and the state panel would be full of
plumbing. So the repository is `<workspace>/repo` and the plumbing is its
sibling.

**Disposal is the Windows papercut this file exists to absorb.** `shutil.rmtree`
fails with `WinError 5` on a git object, because git marks loose objects
read-only and Windows honours that against deletion. Proven by running it, not
reasoned about: the first disposal of a provisioned workspace raised
`PermissionError` on `objects/0b/2626fa...`.
"""

from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from practice.adapters.sandbox.env import SandboxClock, SandboxPaths, with_commit_date
from practice.adapters.sandbox.execution import OUTPUT_LIMIT_BYTES, run_process
from practice.adapters.sandbox.virtual_commands import is_virtual, run_virtual
from practice.domain.attempt import CommandResult
from practice.domain.errors import InvalidValueError
from practice.domain.ids import Sha

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.adapters.sandbox.command_policy import CommandPolicy
    from practice.adapters.sandbox.execution import Execution

__all__ = ["SubprocessWorkspace", "WorkspaceLayout", "WorkspacePathError"]

#: The repository the solver works in. Everything else in the workspace is
#: plumbing that deliberately sits outside it.
_REPO_DIRNAME: Final = "repo"

#: A name and a hash. Any other field count is a malformed line.
_MAP_FIELDS: Final = 2


class WorkspacePathError(Exception):
    """A path argument pointed outside the workspace, so nothing was done.

    Not a security boundary — the solver is the author of their own machine
    (PLAN.md §8.1). It is a blast-radius boundary: a `write ../../.bashrc` is
    almost certainly a typo, and the useful response to a typo is to refuse it
    and say where the boundary is.
    """


@dataclass(frozen=True, slots=True)
class WorkspaceLayout:
    """Every path in a workspace, derived from its root.

    One place that knows the shape, so the provisioner that creates these files,
    the fixture runner that writes them, the workspace that reads them and the
    collector that deletes them cannot disagree about where they are.
    """

    root: Path

    @property
    def repo(self) -> Path:
        """The repository the solver runs commands in."""
        return self.root / _REPO_DIRNAME

    @property
    def remotes(self) -> Path:
        """Bare repositories standing in for remotes. There is no network."""
        return self.root / "remotes"

    @property
    def tmp(self) -> Path:
        """`TMPDIR` for sandboxed processes, so git's temp files stay inside."""
        return self.root / "tmp"

    @property
    def lib(self) -> Path:
        """Where `fixture_lib.sh` is copied to."""
        return self.root / "lib"

    @property
    def fixture_lib(self) -> Path:
        return self.lib / "fixture_lib.sh"

    @property
    def fixture(self) -> Path:
        return self.root / "fixture.sh"

    @property
    def gitconfig(self) -> Path:
        """`GIT_CONFIG_GLOBAL`, and also `~/.gitconfig` since `HOME` is root."""
        return self.root / ".gitconfig"

    @property
    def aliases(self) -> Path:
        """`c1=<sha>` lines appended by the fixture's `commit_as`."""
        return self.root / "aliases"

    @property
    def snapshot(self) -> Path:
        """Every ref as it stood when the fixture finished (PLAN.md §6.1)."""
        return self.root / "snapshot"

    @property
    def clock(self) -> Path:
        """The commit clock's position, shared between bash and Python."""
        return self.root / "clock"

    @property
    def metadata(self) -> Path:
        """What `practice gc` reads to describe a workspace it did not create."""
        return self.root / "workspace.json"

    @property
    def exists(self) -> bool:
        return self.root.is_dir()

    def paths(self) -> SandboxPaths:
        """The subset a sandboxed process is told about, as environment."""
        return SandboxPaths(
            home=self.root,
            repo=self.repo,
            remotes=self.remotes,
            tmp=self.tmp,
            gitconfig=self.gitconfig,
            fixture_lib=self.fixture_lib,
            aliases=self.aliases,
            snapshot=self.snapshot,
            clock=self.clock,
        )

    def create(self) -> None:
        """Make the directory skeleton. Idempotent, so resume can call it."""
        for directory in (self.root, self.repo, self.remotes, self.tmp, self.lib):
            directory.mkdir(parents=True, exist_ok=True)

    def destroy(self) -> None:
        """Delete the whole tree, read-only git objects and all.

        The `onexc` handler is not defensive programming; without it, disposing
        of any workspace that has ever held a commit fails on Windows. Git marks
        loose objects read-only, Windows refuses to delete a read-only file, and
        the error names an object path that looks like corruption rather than a
        permission model.
        """
        if not self.root.exists():
            return
        shutil.rmtree(self.root, onexc=_force_remove)


def _force_remove(function: object, path: str, _exception: BaseException) -> None:
    """Clear the read-only bit and retry once.

    A second failure is allowed to propagate: it means something genuinely has
    the file open — on Windows, usually a process a timeout failed to kill —
    and silently leaving a half-deleted workspace behind would make
    `practice gc` report something that cannot be collected.
    """
    del function
    target = Path(path)
    target.chmod(stat.S_IWRITE | stat.S_IREAD)
    if target.is_dir():
        target.rmdir()
    else:
        target.unlink()


class SubprocessWorkspace:
    """Satisfies `practice.domain.ports.Workspace` over a real directory.

    Structurally, not by inheritance: the port is a `Protocol`, so this class
    does not import it and the dependency arrow keeps pointing inward (ADR
    0002).

    **It enforces the command policy even though its caller already did.** The
    same deliberate duplication `Attempt.record_command` documents: the use case
    refuses to *offer* a disallowed command, the aggregate refuses to *remember*
    one, and this refuses to *execute* one. A future code path that forgets the
    gate gets a readable rejection rather than an exercise whose allowlist
    quietly did not apply.
    """

    __slots__ = (
        "_clock",
        "_environment",
        "_layout",
        "_output_limit",
        "_policy",
    )

    def __init__(
        self,
        layout: WorkspaceLayout,
        *,
        policy: CommandPolicy,
        environment: Mapping[str, str],
        output_limit: int = OUTPUT_LIMIT_BYTES,
    ) -> None:
        self._layout = layout
        self._policy = policy
        self._environment = dict(environment)
        self._output_limit = output_limit
        self._clock = SandboxClock(layout.clock)

    @property
    def layout(self) -> WorkspaceLayout:
        return self._layout

    @property
    def root(self) -> Path:
        return self._layout.root

    @property
    def repo(self) -> Path:
        """Where commands run, and what `GitRepoQuery` will interrogate."""
        return self._layout.repo

    @property
    def policy(self) -> CommandPolicy:
        return self._policy

    # --- the Workspace port -------------------------------------------------

    def run(self, argv: Sequence[str], timeout: float) -> CommandResult:
        """Run one already-parsed command in the repository.

        The clock advances on every command rather than only on commits. Knowing
        which commands commit would mean parsing git's own argument grammar —
        `git commit`, `git merge --no-ff`, `git revert`, `git cherry-pick`, `git
        rebase --continue` — and being wrong about any one of them loses
        determinism. Advancing unconditionally costs nothing: the dates are only
        read when a commit is actually made.
        """
        self._policy.vet(argv)
        if is_virtual(argv[0]):
            execution = run_virtual(
                argv, root=self._layout.repo, output_limit=self._output_limit
            )
        else:
            execution = run_process(
                argv,
                cwd=self._layout.repo,
                environment=with_commit_date(self._environment, self._clock.tick()),
                timeout=timeout,
                output_limit=self._output_limit,
            )
        return _as_command_result(execution)

    def run_tool(self, argv: Sequence[str], timeout: float) -> CommandResult:
        """Run a trusted tool in the workspace, outside the exercise's allowlist.

        The other half of the trust split from `run` (PLAN.md §8.1), and the
        reason it is a separate method rather than a flag: `run` is whatever the
        solver typed and `run_tool` is an argv a grading engine built for
        itself. The kata engine's `python -m pytest` is the first caller, and
        no allowlist could gate it — a kata's allowlist is empty by design,
        because a kata has no command console at all.

        **Never pass user input here.** It receives the same scoped environment
        and the same output caps as `run`, and nothing else: it is the policy
        gate that is missing, which is exactly what makes it dangerous to reach
        for from a route handler.

        The clock is read rather than advanced. A grading pass interrogates the
        repository and must not move the commit clock while doing it — a
        `GitRepoQuery` call that consumed a tick would make the dates of a
        solver's later commits depend on how many times they looked at the
        verdict.
        """
        execution = run_process(
            argv,
            cwd=self._layout.repo,
            environment=with_commit_date(self._environment, self._clock.read()),
            timeout=timeout,
            output_limit=self._output_limit,
        )
        return _as_command_result(execution)

    def read_file(self, path: str) -> str:
        """Read a file from the repository, as the web editor needs to."""
        return self.resolve(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> None:
        """Write a file into the repository, with LF endings on every platform.

        Newline translation is disabled explicitly. Letting Python write CRLF on
        Windows would change the blob, and therefore the tree, and therefore
        every commit hash downstream of it — the exact failure PLAN.md §6.1 pins
        `core.autocrlf` and `.gitattributes` to prevent, reintroduced from the
        other side.
        """
        target = self.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="")

    def dispose(self) -> None:
        """Delete the workspace. Safe to call twice."""
        self._layout.destroy()

    # --- what grading will read --------------------------------------------

    def aliases(self) -> Mapping[str, Sha]:
        """The fixture's symbolic names, for resolving `@c2` in an assertion."""
        return read_sha_map(self._layout.aliases, separator="=")

    def snapshot(self) -> Mapping[str, Sha]:
        """Every ref as the fixture left it, for `ref_unchanged`."""
        return read_sha_map(self._layout.snapshot, separator=None)

    # --- paths --------------------------------------------------------------

    def resolve(self, path: str) -> Path:
        """A repository-relative path, confined to the repository.

        Absolute paths and `..` escapes are refused rather than clamped.
        Clamping would turn `write ../notes.md` into a file in an unexpected
        place and leave the solver hunting for it; refusing says what happened.
        """
        candidate = Path(path)
        if candidate.is_absolute() or (os.name == "nt" and candidate.drive):
            raise WorkspacePathError(
                f"{path!r} is an absolute path; use a path inside the repository"
            )
        resolved = (self._layout.repo / candidate).resolve()
        base = self._layout.repo.resolve()
        if resolved != base and base not in resolved.parents:
            raise WorkspacePathError(
                f"{path!r} points outside the repository, so nothing was done"
            )
        return resolved

    def __repr__(self) -> str:
        return f"SubprocessWorkspace(root={self._layout.root})"


def read_sha_map(path: Path, *, separator: str | None = None) -> Mapping[str, Sha]:
    """Parse a `<name><separator><sha>` file into a mapping.

    Shared by the alias map (written by bash, `=` separated) and the ref
    snapshot (written by the fixture runner, whitespace separated) because they
    are the same file format twice, and a second parser would be a second place
    for a malformed line to mean something different.

    A line that is not two fields, or whose second field is not a hash, is
    skipped rather than fatal. Both files are written by trusted code, so a bad
    line means a fixture bug — and a fixture bug should cost one assertion its
    target, not take down the whole grading pass with a parse error.
    """
    if not path.is_file():
        return {}

    found: dict[str, Sha] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.strip().split(separator, 1) if separator else line.split()
        if len(fields) != _MAP_FIELDS:
            continue
        name, raw = fields[0].strip(), fields[1].strip()
        try:
            found[name] = Sha(raw)
        except InvalidValueError:
            continue
    return found


def _as_command_result(execution: Execution) -> CommandResult:
    """Drop `timed_out` on the way into the domain.

    The domain models a command that produced an exit code; the invented 124 and
    the note appended to stderr are this layer's explanation of it, and are
    already in the fields the domain does keep.
    """
    return CommandResult(
        exit_code=execution.exit_code,
        stdout=execution.stdout,
        stderr=execution.stderr,
        duration_ms=execution.duration_ms,
        truncated=execution.truncated,
    )
