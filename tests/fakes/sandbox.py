"""A workspace and a provisioner with no filesystem behind them.

The second implementation of two ports, and the pair that makes the application
tests possible: `StartAttempt` and `SubmitSolution` are about ordering and error
handling, and proving they get those right should not cost a git process and a
temp directory per case.

**They are not merely stubs — they keep the ports honest.** `FakeWorkspace`
records every `run` and `run_tool` call and refuses to pretend it was disposed
twice;
`FakeProvisioner` refuses to provision over an existing workspace and returns
`None` from `attach` when there is nothing there, which is exactly what
`SubprocessSandboxProvisioner` does. Where a fake is allowed to differ from the
real adapter, the test using it proves nothing.

The Phase 6 addition is the pair `practice gc` runs on: `workspaces()` reports
what is on disk and `discard()` deletes one by its directory name. Both are held
to the real adapter in the detail that decides the orphan rule — a workspace
whose metadata was never written still appears in the listing, with a `short_id`
and no `attempt_id`, because an interrupted provision is exactly the leftover gc
exists to find.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.attempt import CommandResult
from practice.domain.ports import WorkspaceSummary

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.domain.exercise import Exercise
    from practice.domain.ids import AttemptId, Sha

__all__ = ["FakeProvisioner", "FakeWorkspace"]


class FakeWorkspace:
    """Satisfies `practice.domain.ports.Workspace` over a dict of files."""

    def __init__(
        self,
        files: dict[str, str] | None = None,
        *,
        aliases: Mapping[str, Sha] | None = None,
        snapshot: Mapping[str, Sha] | None = None,
    ) -> None:
        self.files: dict[str, str] = dict(files or {})
        self.commands: list[tuple[str, ...]] = []
        self.tools: list[tuple[str, ...]] = []
        self.disposed = False
        #: What `run` answers. Settable because a console transcript is mostly
        #: *output*, and the cases worth asserting on -- a conflict on stderr, a
        #: non-zero exit, capped output -- are differences in the result rather
        #: than in the argv. A fake that could only succeed silently would make
        #: every one of them untestable without a real git.
        self.result = CommandResult(exit_code=0)
        self._aliases: dict[str, Sha] = dict(aliases or {})
        self._snapshot: dict[str, Sha] = dict(snapshot or {})

    def run(self, argv: Sequence[str], timeout: float) -> CommandResult:
        del timeout
        self.commands.append(tuple(argv))
        return self.result

    def run_tool(self, argv: Sequence[str], timeout: float) -> CommandResult:
        del timeout
        self.tools.append(tuple(argv))
        return CommandResult(exit_code=0)

    def read_file(self, path: str) -> str:
        """Raises the same thing a real one does for a file that is not there.

        `FileNotFoundError` rather than `KeyError`, because callers catch
        `OSError` — `PytestKataRunner` reads a report that may not exist and
        treats the absence as "the suite did not run".
        """
        try:
            return self.files[path]
        except KeyError as exc:
            raise FileNotFoundError(path) from exc

    def write_file(self, path: str, content: str) -> None:
        self.files[path] = content

    def aliases(self) -> Mapping[str, Sha]:
        """Empty by default, like a kata's workspace, where no fixture ran."""
        return dict(self._aliases)

    def snapshot(self) -> Mapping[str, Sha]:
        return dict(self._snapshot)

    def dispose(self) -> None:
        self.disposed = True


class FakeProvisioner:
    """Satisfies `practice.domain.ports.SandboxProvisioner` with a dict.

    The live workspaces are reached through `workspace_for` rather than a public
    dict, because `workspaces()` is the port's own listing and a fake cannot have
    both under one name. Which is the better arrangement anyway: a test asking for
    *the* workspace of an attempt and a test asking what is on disk are asking
    different questions.
    """

    def __init__(self) -> None:
        self._workspaces: dict[AttemptId, FakeWorkspace] = {}
        self.provisioned: list[tuple[str, AttemptId]] = []
        #: Short ids that are on disk with no live workspace behind them: what an
        #: interrupted provision leaves, and what `gc` is for.
        self._stray: list[str] = []
        self.discarded: list[str] = []

    def provision(self, exercise: Exercise, attempt_id: AttemptId) -> FakeWorkspace:
        if attempt_id in self._workspaces:
            raise AssertionError(f"already provisioned: {attempt_id.short}")
        workspace = FakeWorkspace()
        self._workspaces[attempt_id] = workspace
        self.provisioned.append((str(exercise.id), attempt_id))
        return workspace

    def attach(self, exercise: Exercise, attempt_id: AttemptId) -> FakeWorkspace | None:
        """`None` for a workspace that is not there, like the real one."""
        del exercise
        workspace = self._workspaces.get(attempt_id)
        if workspace is None or workspace.disposed:
            return None
        return workspace

    def workspaces(self) -> Sequence[WorkspaceSummary]:
        """What is on disk, in a stable order, described as the real one does.

        A disposed workspace is gone, which is what makes `gc` have nothing to do
        in the normal case; a stray one has a `short_id` and nothing else, which is
        what makes the orphan rule testable without writing a broken directory.
        """
        live = [
            WorkspaceSummary(
                short_id=attempt_id.short,
                attempt_id=attempt_id,
                created_at="2026-10-02T09:00:00+00:00",
                size_bytes=1024,
            )
            for attempt_id, workspace in self._workspaces.items()
            if not workspace.disposed
        ]
        stray = [
            WorkspaceSummary(short_id=short_id, size_bytes=512)
            for short_id in self._stray
        ]
        return tuple(sorted([*live, *stray], key=lambda found: found.short_id))

    def discard(self, short_id: str) -> None:
        """Delete by directory name, which is all gc has for an undescribed one."""
        self.discarded.append(short_id)
        self._stray = [kept for kept in self._stray if kept != short_id]
        for attempt_id in list(self._workspaces):
            if attempt_id.short == short_id:
                del self._workspaces[attempt_id]

    # --- what a test reaches for ------------------------------------------

    def workspace_for(self, attempt_id: AttemptId) -> FakeWorkspace:
        """The workspace provisioned for this attempt. Raises if there is none."""
        return self._workspaces[attempt_id]

    def leave_stray(self, short_id: str) -> None:
        """Put a workspace on disk that no attempt has ever owned.

        An interrupted provision, or an attempt row deleted from under it. The only
        way to produce the state `gc` is built to collect without one.
        """
        self._stray.append(short_id)

    def collect(self, attempt_id: AttemptId) -> None:
        """Delete a workspace behind the application's back.

        What `practice gc` does as of Phase 6, and the only way to test the
        `WorkspaceGoneError` path without deleting a real directory mid-attempt.
        """
        self._workspaces.pop(attempt_id, None)
