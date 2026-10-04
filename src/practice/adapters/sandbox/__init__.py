"""The sandbox: a throwaway directory an attempt runs real commands inside.

Ten modules, split by what each one knows about:

* `env` — the environment a sandboxed process gets, where git is installed, and
  the commit clock that spans the whole attempt. Knows about reproducibility.
* `execution` — one process, one timeout, one capped pair of output streams.
  Knows about `subprocess`, and how to kill a process tree on two platforms.
* `command_policy` — the gate between a typed line and a running process. Knows
  about the exercise's allowlist.
* `virtual_commands` — `write`, `cat`, `ls` and friends in Python, because user
  input never reaches a shell. Knows about files.
* `workspace` — the directory, and the `Workspace` port over it.
* `editor` — the solver's own editor, opened on a file in the workspace. The one
  process start here that is deliberately *not* sandboxed, and it is here
  anyway: the architecture test allows exactly one package to start a process,
  and relaxing that to two would cost more than the oddity of this one living
  next to the two that are scoped (PLAN.md §16, Phase 10).
* `browser` — the solver's browser, opened on the URL `practice up` bound.
  Here for the same reason `editor` is, and the module docstring says what the
  architecture test would and would not have caught.
* `watcher` — notices the solver saving that file, over `watchfiles`. Knows
  that editors save by rename rather than by writing in place.
* `fixture_runner` — finds the bash git bundles, and runs a fixture under the
  pinned environment. Knows how Git for Windows lays itself out.
* `provisioner` — builds a workspace, runs its fixture, finds the ones already
  built, and deletes one nothing owns any more. What it reports about a workspace
  it did not create is a `WorkspaceSummary`, which is port vocabulary rather than
  a type of its own: the only question anyone asks of that list is the orphan
  rule, and that rule is a use case (PLAN.md §8.1).

The split that matters is the one PLAN.md §8.1 calls the trust split: **fixtures
are trusted code, user commands are untrusted input.** A fixture is authored by
whoever wrote the exercise and gets a real bash shell. A solver's command is
parsed into an argv, checked against an allowlist, and handed to a process that
never sees a shell. Those two paths share the environment and the executor and
nothing else, which is why they are separate modules rather than one
`run_something`.

This is **not** a security boundary against a determined attacker — you author
all the content and it runs on your own machine. It is a correctness and
blast-radius boundary, and ADR 0005 is careful about that difference.

**Why `fixture_runner` is here rather than under `adapters/git/`**, where
PLAN.md §10 drew it: it reaches into the sandbox's environment, executor and
workspace, while the provisioner reaches into it — so with the git package
re-exporting it, the two packages imported each other and Python said so. The
dependency that is actually one-directional is the one this layout follows:
everything that *builds* a repository is the sandbox, and `adapters/git/` is for
the half that *reads* one — `GitRepoQuery` and the commit graph, in Phase 5.
Recorded in PLAN.md §16.
"""

from practice.adapters.sandbox.browser import open_in_browser
from practice.adapters.sandbox.command_policy import (
    CommandPolicy,
    CommandRejectedError,
)
from practice.adapters.sandbox.editor import (
    DEFAULT_EDITOR,
    EDITOR_ENV,
    SubprocessEditorLauncher,
    editor_argv,
)
from practice.adapters.sandbox.env import (
    SandboxClock,
    ToolNotFoundError,
    find_git,
    sandbox_environment,
)
from practice.adapters.sandbox.execution import Execution, run_process
from practice.adapters.sandbox.fixture_lock import (
    LOCK_FILENAME,
    FixtureFingerprint,
    fingerprint_library,
)
from practice.adapters.sandbox.fixture_runner import (
    FixtureError,
    FixtureResult,
    find_bash,
    run_fixture,
)
from practice.adapters.sandbox.provisioner import (
    SubprocessSandboxProvisioner,
    WorkspaceExistsError,
)
from practice.adapters.sandbox.virtual_commands import VIRTUAL_COMMANDS, is_virtual
from practice.adapters.sandbox.watcher import TICK_SECONDS, WatchfilesFileWatcher
from practice.adapters.sandbox.workspace import (
    SubprocessWorkspace,
    WorkspaceLayout,
    WorkspacePathError,
)

__all__ = [
    "DEFAULT_EDITOR",
    "EDITOR_ENV",
    "LOCK_FILENAME",
    "TICK_SECONDS",
    "VIRTUAL_COMMANDS",
    "CommandPolicy",
    "CommandRejectedError",
    "Execution",
    "FixtureError",
    "FixtureFingerprint",
    "FixtureResult",
    "SandboxClock",
    "SubprocessEditorLauncher",
    "SubprocessSandboxProvisioner",
    "SubprocessWorkspace",
    "ToolNotFoundError",
    "WatchfilesFileWatcher",
    "WorkspaceExistsError",
    "WorkspaceLayout",
    "WorkspacePathError",
    "editor_argv",
    "find_bash",
    "find_git",
    "fingerprint_library",
    "is_virtual",
    "open_in_browser",
    "run_fixture",
    "run_process",
    "sandbox_environment",
]
