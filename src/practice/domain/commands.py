"""Turning a typed line into an argv, and a `.cmds` file into a list of them.

Pure string handling, so it belongs in the domain even though its first two
callers are adapters. The alternative — a copy in the content validator and
another in the Phase 3 sandbox — is the specific failure PLAN.md §5.3 is about:
if the rules a reference solution is validated against are not byte-for-byte the
rules a solver's input is executed against, then CI proves a solution exists
rather than a solution exists *within the rules*, and a scenario can ship
unsolvable with a green build. One implementation, two callers.

**User input never reaches a shell** (PLAN.md §8.1). `parse_command_line` returns
an argv list and nothing ever reassembles it into a string for `sh -c`, so there
is no injection surface to defend — the metacharacter rejection below is not a
security boundary. It exists because `echo x > file` would otherwise *silently
not redirect*, leaving the solver staring at a file that did not change. Failing
loudly and saying "use `write`" teaches; doing nothing quietly does not.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Final

from practice.domain.errors import InvalidValueError

__all__ = [
    "SHELL_METACHARACTERS",
    "CommandLine",
    "parse_command_line",
    "parse_command_list",
]

#: Characters that mean something to a shell and nothing here. `$` on its own is
#: absent deliberately: the sequence that would expand is `$(`, and a bare `$` is
#: a legal character in a filename that no shell is going to see anyway.
SHELL_METACHARACTERS: Final = frozenset("|<>&;`")

_COMMAND_SUBSTITUTION: Final = "$("

#: The virtual commands that exist precisely because there is no shell, offered
#: in the error message so the rejection comes with its own remedy (§8.1).
_REDIRECTION_ALTERNATIVES: Final = "write, append, rm, mkdir"

_COMMENT: Final = "#"


@dataclass(frozen=True, slots=True)
class CommandLine:
    """One parsed line of a `.cmds` file, with the line it came from.

    `lineno` is 1-based and counts every line of the source file, comments and
    blanks included, so a validation failure points at the line a text editor
    shows rather than at an index into the commands that survived parsing.
    """

    lineno: int
    argv: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.argv:
            raise InvalidValueError("a command line needs an argv")

    @property
    def program(self) -> str:
        return self.argv[0]

    @property
    def text(self) -> str:
        """The normalised single line, as `CommandRun.command_line` renders it."""
        return shlex.join(self.argv)


def parse_command_line(line: str) -> tuple[str, ...]:
    """Split one typed line into an argv, or explain why it is not one.

    Raises `InvalidValueError` — which is also a `ValueError`, so a Pydantic field
    validator that calls this reports it against the right field (PLAN.md §4.1).
    """
    for character in line:
        if character in SHELL_METACHARACTERS:
            raise InvalidValueError(
                f"{character!r} is a shell character and there is no shell here; "
                f"for file operations use {_REDIRECTION_ALTERNATIVES}"
            )
    if _COMMAND_SUBSTITUTION in line:
        raise InvalidValueError(
            "'$(' is command substitution and there is no shell here"
        )

    try:
        argv = shlex.split(line)
    except ValueError as exc:  # an unbalanced quote is the only way in
        raise InvalidValueError(f"cannot be split into arguments: {exc}") from exc

    if not argv:
        raise InvalidValueError("is not a command")
    return tuple(argv)


def parse_command_list(text: str) -> tuple[CommandLine, ...]:
    """Parse a `.cmds` file: one command per line, `#` comments and blanks ignored.

    Comments are whole-line only — a `#` is stripped when it is the first
    non-whitespace character on the line and is an ordinary argument character
    anywhere else. Trailing comments would be the friendlier rule right up until
    the first `git log --format=%h#%s`, and a format string that silently loses
    half itself is a worse failure than not being allowed to annotate a line.
    """
    commands: list[CommandLine] = []
    for index, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(_COMMENT):
            continue
        try:
            argv = parse_command_line(line)
        except InvalidValueError as exc:
            raise InvalidValueError(f"line {index}: {line!r} {exc}") from exc
        commands.append(CommandLine(lineno=index, argv=argv))
    return tuple(commands)
