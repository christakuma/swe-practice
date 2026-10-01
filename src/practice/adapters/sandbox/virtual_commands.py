"""File operations implemented in Python, because there is no shell.

User input is never handed to a shell (PLAN.md §8.1), which means `echo x > f`
cannot work — the `>` is rejected before anything runs. The alternative to
re-admitting shell parsing is to implement the handful of file operations people
actually need, which is what this module is. Cross-platform for free, and the
input surface stays an argv list.

**`pwd` is here, and finding that out is the point of building before
designing.** §8.1 lists six commands — `write`, `append`, `rm`, `mkdir`, `cat`,
`ls` — but `content/git/revert-a-pushed-commit/exercise.yaml` had already
shipped `pwd` in its `allowlist`, and `pwd` is a shell builtin with no
executable behind it on Windows. Without it here, a solver typing `pwd` on an
exercise that explicitly permits it would get `command not found`.

**They imitate the real tools rather than improving on them.** Same flags, same
exit codes, same shape of error message — `rm: cannot remove 'x': No such file
or directory`. A console that teaches operational git by inventing its own
dialect of `rm` is teaching the wrong thing.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Final

from practice.adapters.sandbox.execution import (
    OUTPUT_LIMIT_BYTES,
    TRUNCATION_MARKER,
    Execution,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["VIRTUAL_COMMANDS", "is_virtual", "run_virtual"]

#: Every command implemented here. An exercise still has to list the ones it
#: wants in `allowed_commands`: being virtual makes a command *possible*, not
#: *permitted*.
VIRTUAL_COMMANDS: Final = frozenset(
    {"append", "cat", "ls", "mkdir", "pwd", "rm", "write"}
)

#: What the real tools return. 2 for "you typed it wrong", 1 for "it did not
#: work", matching coreutils closely enough that the habit transfers.
_USAGE: Final = 2
_FAILED: Final = 1


def is_virtual(program: str) -> bool:
    """Whether `program` is implemented here rather than executed."""
    return program in VIRTUAL_COMMANDS


def run_virtual(
    argv: Sequence[str],
    *,
    root: Path,
    output_limit: int = OUTPUT_LIMIT_BYTES,
) -> Execution:
    """Run one virtual command inside `root`.

    No timeout parameter: every operation here is a bounded filesystem call on a
    small repository, so there is nothing to time out. If that stops being true
    the honest fix is a real process, not a thread with a watchdog.
    """
    program, *arguments = argv
    handler = _HANDLERS.get(program)
    if handler is None:  # pragma: no cover — `is_virtual` is checked first
        return _fail(f"{program}: not a virtual command", code=_USAGE)
    try:
        return handler(program, arguments, root, output_limit)
    except _VirtualError as exc:
        return _fail(str(exc), code=exc.code)
    except OSError as exc:
        # Anything the filesystem itself refuses: a directory where a file was
        # expected, a name the platform will not accept, a permission bit.
        return _fail(f"{program}: {exc.strerror or exc}", code=_FAILED)


# --- the commands ----------------------------------------------------------


def _write(
    program: str, arguments: Sequence[str], root: Path, _limit: int
) -> Execution:
    """`write <path> [line ...]` — replace a file with these lines.

    Zero lines truncates to empty, which is what `> file` does and the reason
    anyone reaches for redirection in the first place. Every line gets a
    trailing LF on every platform: a CRLF here would change the blob, the tree,
    and every commit hash after it (PLAN.md §6.1).
    """
    path = _one_path(program, arguments, root, usage="write <path> [line ...]")
    _write_lines(path, arguments[1:], append=False)
    return Execution(exit_code=0)


def _append(
    program: str, arguments: Sequence[str], root: Path, _limit: int
) -> Execution:
    """`append <path> [line ...]` — add these lines to the end of a file."""
    path = _one_path(program, arguments, root, usage="append <path> [line ...]")
    _write_lines(path, arguments[1:], append=True)
    return Execution(exit_code=0)


def _cat(program: str, arguments: Sequence[str], root: Path, limit: int) -> Execution:
    """`cat <path> ...` — print files, in order.

    Reads as bytes and decodes with replacement, because a solver can commit
    anything and `cat` on a binary file should print mojibake like the real one
    rather than raise.
    """
    if not arguments:
        raise _VirtualError(f"usage: {program} <path> ...", code=_USAGE)
    chunks = []
    for argument in arguments:
        path = _resolve(program, argument, root)
        if path.is_dir():
            raise _VirtualError(f"{program}: {argument}: Is a directory")
        if not path.exists():
            raise _VirtualError(f"{program}: {argument}: No such file or directory")
        chunks.append(path.read_bytes().decode("utf-8", errors="replace"))
    return _output("".join(chunks).replace("\r\n", "\n"), limit)


def _ls(program: str, arguments: Sequence[str], root: Path, limit: int) -> Execution:
    """`ls [-a] [path ...]` — list directory contents, one name per line.

    Dotfiles are hidden without `-a`, which is the real behaviour and matters
    here: `.git` is a dotfile, and a bare `ls` that showed it would make every
    listing about plumbing instead of about the solver's files. Directories get
    a trailing slash, the one deviation, because the alternative is `-F` and the
    information is worth more than the fidelity.
    """
    flags, operands = _split_flags(arguments, known={"-a"})
    show_all = "-a" in flags
    targets = operands or ["."]

    sections = []
    for argument in targets:
        path = _resolve(program, argument, root)
        if not path.exists():
            raise _VirtualError(
                f"{program}: cannot access '{argument}': No such file or directory"
            )
        if path.is_file():
            sections.append((argument, [argument]))
            continue
        names = sorted(
            f"{child.name}/" if child.is_dir() else child.name
            for child in path.iterdir()
            if show_all or not child.name.startswith(".")
        )
        sections.append((argument, names))

    if len(sections) == 1:
        body = "".join(f"{name}\n" for name in sections[0][1])
    else:
        body = "\n".join("\n".join([f"{label}:", *names]) for label, names in sections)
        body = f"{body}\n" if body else ""
    return _output(body, limit)


def _mkdir(
    program: str, arguments: Sequence[str], root: Path, _limit: int
) -> Execution:
    """`mkdir [-p] <path> ...` — create directories.

    Without `-p` a missing parent or an existing target is an error, as it is in
    the real thing. Getting that wrong would teach `-p` as decoration.
    """
    flags, operands = _split_flags(arguments, known={"-p"})
    parents = "-p" in flags
    if not operands:
        raise _VirtualError(f"usage: {program} [-p] <path> ...", code=_USAGE)
    for argument in operands:
        path = _resolve(program, argument, root)
        if path.exists():
            if parents:
                continue
            raise _VirtualError(
                f"{program}: cannot create directory '{argument}': File exists"
            )
        if not parents and not path.parent.is_dir():
            raise _VirtualError(
                f"{program}: cannot create directory '{argument}': "
                f"No such file or directory"
            )
        path.mkdir(parents=parents, exist_ok=parents)
    return Execution(exit_code=0)


def _rm(program: str, arguments: Sequence[str], root: Path, _limit: int) -> Execution:
    """`rm [-r] [-f] <path> ...` — delete files, and with `-r` directories.

    Refusing to remove a directory without `-r` is kept deliberately: an
    exercise about recovering from a destructive command should not have a
    `rm` that is quieter than the real one.
    """
    flags, operands = _split_flags(arguments, known={"-r", "-rf", "-f", "-fr", "-R"})
    recursive = any(flag in {"-r", "-R", "-rf", "-fr"} for flag in flags)
    force = any(flag in {"-f", "-rf", "-fr"} for flag in flags)
    if not operands:
        if force:
            return Execution(exit_code=0)
        raise _VirtualError(f"usage: {program} [-r] [-f] <path> ...", code=_USAGE)

    for argument in operands:
        path = _resolve(program, argument, root)
        if not path.exists():
            if force:
                continue
            raise _VirtualError(
                f"{program}: cannot remove '{argument}': No such file or directory"
            )
        if path == root.resolve():
            # The real `rm` refuses this too, and here it matters more: taking
            # the repository would take `.git` with it, leaving an attempt that
            # cannot be graded and a failure that looks like a tool bug rather
            # than something the solver did. Found by a test, not by thinking
            # about it — `-f` made it silent as well as destructive.
            raise _VirtualError(
                f"{program}: refusing to remove '{argument}', the repository itself"
            )
        if path.is_dir():
            if not recursive:
                raise _VirtualError(
                    f"{program}: cannot remove '{argument}': Is a directory"
                )
            shutil.rmtree(path)
        else:
            path.unlink()
    return Execution(exit_code=0)


def _pwd(program: str, arguments: Sequence[str], root: Path, limit: int) -> Execution:
    """`pwd` — print the repository directory.

    There is no `cd`, so this always prints the same path. It is still worth
    having: it is the first thing people type when they are not sure where they
    are, and the answer should be the real path rather than a fiction.
    """
    if arguments:
        raise _VirtualError(f"usage: {program}", code=_USAGE)
    return _output(f"{root.resolve().as_posix()}\n", limit)


#: Dispatch table. Built after the functions so the names resolve, and keyed by
#: the same strings `VIRTUAL_COMMANDS` holds — a test asserts the two agree,
#: because a command in one and not the other is either unreachable or a
#: `command not found` on something the policy already permitted.
_HANDLERS: Final = {
    "append": _append,
    "cat": _cat,
    "ls": _ls,
    "mkdir": _mkdir,
    "pwd": _pwd,
    "rm": _rm,
    "write": _write,
}


# --- shared helpers --------------------------------------------------------


class _VirtualError(Exception):
    """A command failed the way a real one would, with an exit code to match."""

    def __init__(self, message: str, *, code: int = _FAILED) -> None:
        self.code = code
        super().__init__(message)


def _resolve(program: str, argument: str, root: Path) -> Path:
    """Resolve a path argument, refusing anything outside `root`.

    Duplicated from `SubprocessWorkspace.resolve` in behaviour but not in
    reporting: this one has to fail as a *command* — a message on stderr and a
    non-zero exit — rather than as an exception, because the solver typed it and
    should see it the way they would see any other command failing.
    """
    candidate = Path(argument)
    if candidate.is_absolute() or candidate.drive:
        raise _VirtualError(
            f"{program}: {argument}: absolute paths are outside the repository"
        )
    resolved = (root / candidate).resolve()
    base = root.resolve()
    if resolved != base and base not in resolved.parents:
        raise _VirtualError(
            f"{program}: {argument}: outside the repository, so nothing was done"
        )
    return resolved


def _one_path(
    program: str, arguments: Sequence[str], root: Path, *, usage: str
) -> Path:
    if not arguments:
        raise _VirtualError(f"usage: {usage}", code=_USAGE)
    return _resolve(program, arguments[0], root)


def _write_lines(path: Path, lines: Sequence[str], *, append: bool) -> None:
    body = "".join(f"{line}\n" for line in lines)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8", newline="") as handle:
        handle.write(body)


def _split_flags(
    arguments: Sequence[str], *, known: set[str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Separate leading flags from operands, stopping at the first operand.

    Flags only count before the first operand, so `rm file -r` removes two
    things and does not recurse — which is what the real `rm` does not do, but
    is the safer of the two readings and the one that cannot surprise anyone.
    An unknown flag is an operand, and will fail as a missing path with the
    flag's own name in the message.
    """
    leading = 0
    while leading < len(arguments) and arguments[leading] in known:
        leading += 1
    return tuple(arguments[:leading]), tuple(arguments[leading:])


def _output(body: str, limit: int) -> Execution:
    truncated = len(body.encode("utf-8")) > limit
    if truncated:
        body = body.encode("utf-8")[:limit].decode("utf-8", errors="ignore")
        body += TRUNCATION_MARKER
    return Execution(exit_code=0, stdout=body, truncated=truncated)


def _fail(message: str, *, code: int) -> Execution:
    return Execution(exit_code=code, stderr=f"{message.rstrip()}\n")
