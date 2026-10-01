"""Running one process, with a timeout that actually kills what it started.

Shared by the workspace (solver commands) and the fixture runner (trusted bash),
because both need the same three things and neither should own them: an argv
list that never reaches a shell, output capped so a runaway loop cannot fill
memory or the verdict panel, and a timeout that takes the whole process tree
rather than just the child we can see.

**The tree kill is the interesting part, and the obvious Windows answer is
wrong** (PLAN.md §7, ADR 0005). `subprocess.run(timeout=...)` kills the direct
child only, so a `git` that spawned a helper leaves the helper running and
holding file handles — which on Windows then makes the workspace undeletable.

* **POSIX:** `start_new_session=True` puts the child in its own process group,
  and `os.killpg` takes the group.
* **Windows:** `CREATE_NEW_PROCESS_GROUP` does *not* help. It exists so you can
  send `CTRL_BREAK_EVENT`; `Popen.kill()` still terminates only the direct
  child. The correct answer is a Job Object with
  `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`; the pragmatic one is `taskkill /T /F`,
  which is what v1 does.

**Output is decoded, not streamed.** `communicate()` reads to EOF and the cap is
applied afterwards, so a process that writes gigabytes would still cost
gigabytes of memory before being truncated. Accepted for v1: the sandbox holds a
three-commit repository and the only real program on any exercise's allowlist is
`git`. Stated here rather than discovered later.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "NOT_FOUND_EXIT_CODE",
    "OUTPUT_LIMIT_BYTES",
    "TIMEOUT_EXIT_CODE",
    "TRUNCATION_MARKER",
    "Execution",
    "resolve_program",
    "run_process",
]

#: 64 KB per stream (PLAN.md §8.1). Generous for `git log` on a fixture repo and
#: small enough that the web panel stays responsive.
OUTPUT_LIMIT_BYTES: Final = 64 * 1024

#: What a timed-out command reports. 124 is what GNU `timeout` uses, so anyone
#: who has met it in a shell already knows what it means.
TIMEOUT_EXIT_CODE: Final = 124

#: What an unresolvable program reports, matching the shell convention. The
#: sandbox never reaches a shell, so this is produced here rather than by one.
NOT_FOUND_EXIT_CODE: Final = 127

TRUNCATION_MARKER: Final = "\n... output truncated at 64 KB ...\n"

#: Whether to put the child in its own process group, which is what makes
#: `os.killpg` able to take the whole tree. POSIX only: on Windows the
#: parameter is accepted and ignored, and the equivalent — a Job Object, or
#: `taskkill /T` — cannot be asked for at `Popen` time.
_OWN_PROCESS_GROUP: Final = sys.platform != "win32"

#: How long to wait for a killed tree to actually exit before giving up on
#: collecting its output. A tree that ignores SIGKILL is not something this
#: process can do anything about, and hanging here would turn a command timeout
#: into a hung application.
_REAP_TIMEOUT: Final = 5.0


@dataclass(frozen=True, slots=True)
class Execution:
    """The raw result of one process. Mapped to a `CommandResult` by the caller.

    A separate type from the domain's `CommandResult` because this layer knows
    one thing the domain deliberately does not: whether the process was killed
    for running too long. The domain models a command that produced an exit
    code; `timed_out` is how this adapter explains which exit code it invented.
    """

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    truncated: bool = False
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


def resolve_program(program: str, environment: Mapping[str, str]) -> Path | None:
    """Find `program` on the sandbox's own `PATH`, not on this process's.

    Resolved explicitly, and against the scoped `PATH`, for two reasons. A
    missing program becomes a readable "command not found" instead of a
    `FileNotFoundError` from deep inside `subprocess`. And on Windows,
    `subprocess` would otherwise search the *parent's* `PATH` for a bare name,
    which would quietly undo the scoping that `sandbox_environment` exists for.

    The working directory is never searched, which `shutil.which` with an
    explicit `path` gives for free: on Windows the current directory is
    otherwise searched implicitly, and a repository the solver controls is not
    somewhere to go looking for `git`.
    """
    found = shutil.which(program, path=environment.get("PATH", ""))
    return Path(found) if found else None


def run_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: float,
    output_limit: int = OUTPUT_LIMIT_BYTES,
) -> Execution:
    """Run `argv` to completion, or kill its whole tree trying.

    `argv` is a list and `shell` is never set, so there is no shell to
    reinterpret anything (PLAN.md §8.1). The caller has already applied policy;
    this function is the mechanism, not the gate.
    """
    program = resolve_program(argv[0], environment)
    if program is None:
        return Execution(
            exit_code=NOT_FOUND_EXIT_CODE,
            stderr=f"{argv[0]}: command not found\n",
        )

    started = time.monotonic()
    # S603: an argv list with shell=False, resolved to an absolute executable,
    # under a policy allowlist. Executing commands is the product (ADR 0005).
    process = subprocess.Popen(  # noqa: S603
        [str(program), *argv[1:]],
        cwd=cwd,
        env=dict(environment),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        start_new_session=_OWN_PROCESS_GROUP,
    )

    timed_out = False
    try:
        raw_out, raw_err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(process)
        raw_out, raw_err = _reap(process)

    duration_ms = int((time.monotonic() - started) * 1000)
    stdout, out_truncated = _decode(raw_out, output_limit)
    stderr, err_truncated = _decode(raw_err, output_limit)

    if timed_out:
        note = f"\nTimed out after {timeout:g}s and was killed.\n"
        stderr = f"{stderr}{note}" if stderr else note.lstrip("\n")

    return Execution(
        exit_code=TIMEOUT_EXIT_CODE if timed_out else process.returncode,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
        truncated=out_truncated or err_truncated,
        timed_out=timed_out,
    )


def _kill_tree(process: subprocess.Popen[bytes]) -> None:
    """Kill the child and everything it started. Best effort, never raises.

    Never raises because this runs on the timeout path, where the command has
    already failed and the only thing worse than a surviving grandchild is an
    exception that hides the timeout from the solver.
    """
    if sys.platform == "win32":
        taskkill = shutil.which("taskkill")
        if taskkill is not None:
            # S603: fixed argv, absolute executable, and the only variable is a
            # pid this process owns.
            subprocess.run(  # noqa: S603
                [taskkill, "/T", "/F", "/PID", str(process.pid)],
                capture_output=True,
                check=False,
                timeout=_REAP_TIMEOUT,
            )
    else:
        # Both exceptions below mean the same thing — the process is already
        # gone, or its handles are already closed — and both are the expected
        # case when something else won the race to kill it.
        with suppress(OSError, ValueError):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)

    # Kill the direct child regardless: on Windows `taskkill` may have been
    # absent or may have raced a grandchild into existence, and on POSIX the
    # group kill may have found the group already empty.
    with suppress(OSError, ValueError):
        process.kill()


def _reap(process: subprocess.Popen[bytes]) -> tuple[bytes, bytes]:
    """Collect whatever the killed process had already written.

    Output produced before the timeout is often the most useful thing the solver
    gets back — a `git log` that was most of the way through says more than an
    empty panel — so it is worth one bounded wait to recover it.
    """
    try:
        return process.communicate(timeout=_REAP_TIMEOUT)
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return b"", b""


def _decode(raw: bytes | None, limit: int) -> tuple[str, bool]:
    """Decode to text, cap it, and say whether anything was dropped.

    `errors="replace"` because a solver can commit any bytes they like and a
    `UnicodeDecodeError` in the middle of grading teaches nothing. CRLF is
    normalised so that output captured on Windows compares equal to the same
    output captured on Linux — which matters the moment a test, or a check,
    looks at it.
    """
    if not raw:
        return "", False
    truncated = len(raw) > limit
    text = raw[:limit].decode("utf-8", errors="replace").replace("\r\n", "\n")
    if truncated:
        text += TRUNCATION_MARKER
    return text, truncated
