"""The sandbox: a throwaway directory an attempt runs real commands inside.

Two modules so far, split by what each one knows about:

* `env` -- the environment a sandboxed process gets, where git is installed,
  and the commit clock that spans the whole attempt. Knows about
  reproducibility.
* `execution` -- one process, one timeout, one capped pair of output streams.
  Knows about `subprocess`, and how to kill a process tree on two platforms.

The split this package exists to serve is the one PLAN.md 8.1 calls the trust
split: **fixtures are trusted code, user commands are untrusted input.** A
fixture is authored by whoever wrote the exercise and gets a real bash shell. A
solver's command is parsed into an argv, checked against an allowlist, and
handed to a process that never sees a shell. Those two paths share the
environment and the executor and nothing else, which is why they end up as
separate modules rather than one `run_something`.

This is **not** a security boundary against a determined attacker -- you author
all the content and it runs on your own machine. It is a correctness and
blast-radius boundary, and ADR 0005 is careful about that difference.
"""

from practice.adapters.sandbox.env import (
    SandboxClock,
    ToolNotFoundError,
    find_git,
    sandbox_environment,
)
from practice.adapters.sandbox.execution import Execution, run_process

__all__ = [
    "Execution",
    "SandboxClock",
    "ToolNotFoundError",
    "find_git",
    "run_process",
    "sandbox_environment",
]
