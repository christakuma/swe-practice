"""A workspace and a provisioner with no filesystem behind them.

The second implementation of two ports, and the pair that makes the application
tests possible: `StartAttempt` and `SubmitSolution` are about ordering and error
handling, and proving they get those right should not cost a git process and a
temp directory per case.

**They are not merely stubs — they keep the ports honest.** `FakeWorkspace`
records every `run_tool` call and refuses to pretend it was disposed twice;
`FakeProvisioner` refuses to provision over an existing workspace and returns
`None` from `attach` when there is nothing there, which is exactly what
`SubprocessSandboxProvisioner` does. Where a fake is allowed to differ from the
real adapter, the test using it proves nothing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.attempt import CommandResult

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.domain.exercise import Exercise
    from practice.domain.ids import AttemptId

__all__ = ["FakeProvisioner", "FakeWorkspace"]


class FakeWorkspace:
    """Satisfies `practice.domain.ports.Workspace` over a dict of files."""

    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files: dict[str, str] = dict(files or {})
        self.commands: list[tuple[str, ...]] = []
        self.tools: list[tuple[str, ...]] = []
        self.disposed = False

    def run(self, argv: Sequence[str], timeout: float) -> CommandResult:
        del timeout
        self.commands.append(tuple(argv))
        return CommandResult(exit_code=0)

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

    def dispose(self) -> None:
        self.disposed = True


class FakeProvisioner:
    """Satisfies `practice.domain.ports.SandboxProvisioner` with a dict."""

    def __init__(self) -> None:
        self.workspaces: dict[AttemptId, FakeWorkspace] = {}
        self.provisioned: list[tuple[str, AttemptId]] = []

    def provision(self, exercise: Exercise, attempt_id: AttemptId) -> FakeWorkspace:
        if attempt_id in self.workspaces:
            raise AssertionError(f"already provisioned: {attempt_id.short}")
        workspace = FakeWorkspace()
        self.workspaces[attempt_id] = workspace
        self.provisioned.append((str(exercise.id), attempt_id))
        return workspace

    def attach(self, exercise: Exercise, attempt_id: AttemptId) -> FakeWorkspace | None:
        """`None` for a workspace that is not there, like the real one."""
        del exercise
        workspace = self.workspaces.get(attempt_id)
        if workspace is None or workspace.disposed:
            return None
        return workspace

    def collect(self, attempt_id: AttemptId) -> None:
        """Delete a workspace behind the application's back.

        What `practice gc` will be able to do in Phase 6, and the only way to
        test the `WorkspaceGoneError` path without deleting a real directory
        mid-attempt.
        """
        self.workspaces.pop(attempt_id, None)
