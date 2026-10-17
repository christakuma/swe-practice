"""A Dockerfile, read the way the builder reads it, and the process it ends in.

The parser behind `ParsedBuildQuery` (Phase 22, ADR 0030). **Small on purpose**:
it implements the part of Docker's grammar a graded definition has to get right,
and refuses the rest with a sentence instead of half-reading it.

What it gets right, because an assertion reads each one:

* **Continuations and comments as the builder joins them.** A line ending in
  the escape character continues; a comment line *inside* a continuation is
  dropped, not treated as the end of the instruction. `# escape=`` ` is
  honoured, because a Windows-flavoured Dockerfile that uses it would otherwise
  parse as one enormous `RUN`.
* **Exec form versus shell form**, decided by whether the arguments are a JSON
  array, as Docker decides it. `CMD ["python", "app.py"]` is exec;
  `CMD [python, app.py]` is not valid JSON, so Docker runs it *through a shell*,
  and so does this. That case is worth a test of its own.
* **Process composition** (`compose_process`): `ENTRYPOINT` plus `CMD`, a shell
  form wrapped in the stage's `SHELL`, and an `ENTRYPOINT` resetting an
  inherited `CMD`. All of it is followed through `FROM <earlier stage>`.
* **Build arguments in `FROM` and `USER`**, including `${VAR:-default}`,
  because the pinning lesson is about the image a `FROM ${BASE}` resolves to.

What it refuses: heredocs (`RUN <<EOF`), which are BuildKit syntax with
rules of their own, and an instruction it does not know. Both are reported as
`DockerfileError` with a line number, which the grader turns into the
`definition-parsed` check.

**One assumption, stated where it is made**: an image built `FROM` something
outside this file is taken to have no `ENTRYPOINT`, `CMD` or `USER` of its own
that matters. That holds for the `python` images every exercise uses. It is
false for images like `node`, whose entrypoint is a script, and an exercise
built on one would need the base's config handed in.
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from practice.domain.ports import Instruction, Stage

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "DockerfileError",
    "Lineage",
    "compose_process",
    "lineage",
    "parse",
    "stage_index",
]

#: Every instruction the builder accepts. `ONBUILD` and `MAINTAINER` are legal
#: and inert here; anything else is a typo, and Docker refuses it too.
KEYWORDS: Final = frozenset(
    {
        "ADD", "ARG", "CMD", "COPY", "ENTRYPOINT", "ENV", "EXPOSE", "FROM",
        "HEALTHCHECK", "LABEL", "MAINTAINER", "ONBUILD", "RUN", "SHELL",
        "STOPSIGNAL", "USER", "VOLUME", "WORKDIR",
    }
)  # fmt: skip

#: Instructions whose arguments may be a JSON array, which makes them exec form.
_JSON_CAPABLE: Final = frozenset(
    {"ADD", "CMD", "COPY", "ENTRYPOINT", "RUN", "SHELL", "VOLUME"}
)

#: Instructions whose leading `--name=value` tokens are options, not arguments.
_FLAGGED: Final = frozenset({"ADD", "COPY", "FROM", "HEALTHCHECK", "RUN"})

#: Instructions whose shell form is one command line rather than a token list.
_COMMAND_LINES: Final = frozenset({"CMD", "ENTRYPOINT", "HEALTHCHECK", "RUN"})

_DEFAULT_SHELL: Final = ("/bin/sh", "-c")
#: Shell syntax beyond `&&` and quoting, after which a line stays the shell's.
_SHELL_SYNTAX: Final = re.compile(r"[;|<>()`$\n&]")
_DIRECTIVE: Final = re.compile(r"^#\s*([a-zA-Z][a-zA-Z0-9]*)\s*=\s*(.+?)\s*$")
_HEREDOC: Final = re.compile(r"<<-?\s*[\"']?[A-Za-z_][A-Za-z0-9_]*")
_VARIABLE: Final = re.compile(
    r"\$(?:\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)(?::(?P<op>[-+])(?P<word>[^}]*))?\}"
    r"|(?P<bare>[A-Za-z_][A-Za-z0-9_]*))"
)


class DockerfileError(Exception):
    """A Dockerfile the builder would refuse, or this parser will not guess at.

    The message is the solver's to read, so it names a line and says what to
    do, the way `near "FORM": syntax error` does for a drill.
    """


def parse(text: str) -> tuple[Stage, ...]:
    """Every build stage in `text`, in order. Raises `DockerfileError`."""
    stages: list[Stage] = []
    global_args: dict[str, str] = {}
    current: _Building | None = None

    for number, line in _logical_lines(text):
        instruction = _instruction(number, line)
        if instruction.keyword == "FROM":
            if current is not None:
                stages.append(current.finish())
            current = _from(instruction, global_args)
            continue
        if current is None:
            if instruction.keyword != "ARG":
                raise DockerfileError(
                    f"line {number}: the first instruction must be FROM (only "
                    f"ARG may come before it), not {instruction.keyword}"
                )
            global_args.update(_assignments(instruction))
            continue
        current.instructions.append(instruction)

    if current is None:
        raise DockerfileError("the Dockerfile has no FROM, so there is no image")
    stages.append(current.finish())
    return tuple(stages)


@dataclass(frozen=True, slots=True)
class Lineage:
    """What a stage inherited and set, resolved through every `FROM` in the file."""

    entrypoint: Instruction | None
    cmd: Instruction | None
    shell: tuple[str, ...]
    user: str


def lineage(stages: Sequence[Stage], index: int = -1) -> Lineage:
    """The config a stage ends with, after inheriting from its parent stage.

    `FROM build` inherits everything `build` set; `FROM python:3.12-slim`
    inherits nothing this file can see (the module docstring's assumption).
    """
    stage = stages[index]
    position = index % len(stages)
    parent = stage_index(stages[:position], stage.base)
    state = (
        lineage(stages, parent)
        if parent is not None
        else Lineage(entrypoint=None, cmd=None, shell=_DEFAULT_SHELL, user="root")
    )
    entrypoint, cmd, shell, user = state.entrypoint, state.cmd, state.shell, state.user
    variables: dict[str, str] = {}
    cmd_set_here = False
    for instruction in stage.instructions:
        match instruction.keyword:
            case "ENTRYPOINT":
                entrypoint = instruction
                # BuildKit resets an *inherited* CMD when a stage sets
                # ENTRYPOINT, and keeps one this stage set -- before or after.
                if not cmd_set_here:
                    cmd = None
            case "CMD":
                cmd = instruction
                cmd_set_here = True
            case "SHELL" if instruction.form == "exec" and instruction.args:
                shell = instruction.args
            case "USER" if instruction.args:
                user = _substitute(instruction.args[0], variables)
            case "ARG" | "ENV":
                variables.update(_assignments(instruction))
            case _:
                pass
    return Lineage(entrypoint=entrypoint, cmd=cmd, shell=shell, user=user)


def compose_process(stages: Sequence[Stage]) -> tuple[str, ...]:
    """The argument vector the shipped image starts PID 1 with, as Docker builds it."""
    if not stages:
        return ()
    final = lineage(stages)
    if final.entrypoint is not None:
        if final.entrypoint.form == "shell":
            # A shell-form ENTRYPOINT ignores CMD entirely.
            return _after_exec((*final.shell, final.entrypoint.args[0]))
        return _after_exec((*final.entrypoint.args, *_argv(final.cmd, final.shell)))
    return _after_exec(_argv(final.cmd, final.shell))


def _after_exec(argv: tuple[str, ...]) -> tuple[str, ...]:
    """What PID 1 *becomes* once a `sh -c` line has run, where that is knowable.

    **Every rule here was measured, not remembered** (ADR 0030), against
    `python:3.12-slim`, whose `/bin/sh` is dash 0.5.12:

    * `sh -c 'python w.py'` leaves **dash** as PID 1. Dash does not replace
      itself with a lone command, whatever older blog posts say about shells,
      which is the whole reason the shell form loses `SIGTERM`.
    * `sh -c 'exec python w.py'`, and `sh -c 'a && exec python w.py'`, end
      with **python** as PID 1. The shell's own `exec` replaces it.
    * `bash -c 'python w.py'` and `bash -c 'a && python w.py'` end with
      **python** as PID 1. Bash execs the last simple command of an `&&` list
      on its own.

    Anything with other shell syntax in it (pipes, `;`, redirections,
    substitutions) stays the shell, which is the safe direction: a check about
    PID 1 then fails an answer it might have passed, and never passes one it
    should have failed.
    """
    match argv:
        case (program, "-c", line):
            replacement = _replacement(program.rsplit("/", 1)[-1], line)
            return replacement or argv
        case _:
            return argv


def _replacement(shell: str, line: str) -> tuple[str, ...]:
    """The program that replaces `shell` once `line` has run, or `()` if none does."""
    segments = [segment.strip() for segment in line.split("&&")]
    if shell not in {"sh", "dash", "bash"} or any(
        not segment or _SHELL_SYNTAX.search(segment) for segment in segments
    ):
        return ()
    try:
        last = shlex.split(segments[-1])
    except ValueError:
        return ()
    if last[:1] == ["exec"]:
        return tuple(last[1:])
    return tuple(last) if shell == "bash" else ()


def _argv(instruction: Instruction | None, shell: tuple[str, ...]) -> tuple[str, ...]:
    if instruction is None:
        return ()
    if instruction.form == "exec":
        return instruction.args
    return (*shell, instruction.args[0])


def stage_index(earlier: Sequence[Stage], base: str) -> int | None:
    """The index of the earlier stage `base` names, by alias or by number."""
    for index, stage in enumerate(earlier):
        if stage.name is not None and stage.name.lower() == base.lower():
            return index
    if base.isdigit() and int(base) < len(earlier):
        return int(base)
    return None


@dataclass(slots=True)
class _Building:
    base: str
    name: str | None
    instructions: list[Instruction] = field(default_factory=list)

    def finish(self) -> Stage:
        return Stage(
            base=self.base, name=self.name, instructions=tuple(self.instructions)
        )


def _from(instruction: Instruction, global_args: Mapping[str, str]) -> _Building:
    """A new stage. Its alias is resolved later, by `lineage`, not here."""
    tokens = instruction.args
    match tokens:
        case [_]:
            name = None
        case [_, alias, stage] if alias.lower() == "as":
            name = stage
        case _:
            raise DockerfileError(
                f"line {instruction.line}: FROM takes an image and an optional "
                f"`AS name`, not {' '.join(tokens)!r}"
            )
    base = _substitute(tokens[0], global_args)
    if not base:
        raise DockerfileError(
            f"line {instruction.line}: FROM {tokens[0]} names no image once its "
            f"build arguments are substituted; give the ARG a default"
        )
    return _Building(base=base, name=name)


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Physical lines joined into instructions, numbered by where each started."""
    raw = text.splitlines()
    escape = "\\"
    start = 0
    # Parser directives are only directives at the very top, before anything else.
    for index, line in enumerate(raw):
        match = _DIRECTIVE.match(line.strip())
        if match is None:
            break
        if match.group(1).lower() == "escape":
            escape = match.group(2)
            if escape not in {"\\", "`"}:
                raise DockerfileError(
                    f"line {index + 1}: the escape directive takes \\ or `, "
                    f"not {escape!r}"
                )
        start = index + 1

    lines: list[tuple[int, str]] = []
    pending: list[str] = []
    began = 0
    for index in range(start, len(raw)):
        stripped = raw[index].strip()
        if stripped.startswith("#"):
            continue
        if not pending:
            if not stripped:
                continue
            began = index + 1
        body = raw[index].rstrip()
        if body.endswith(escape):
            pending.append(body[: -len(escape)])
            continue
        pending.append(body)
        lines.append(
            (began, " ".join(part.strip() for part in pending if part.strip()))
        )
        pending = []
    if pending:
        lines.append(
            (began, " ".join(part.strip() for part in pending if part.strip()))
        )
    return lines


def _instruction(number: int, line: str) -> Instruction:
    head, _, rest = line.partition(" ")
    keyword = head.upper()
    if keyword not in KEYWORDS:
        raise DockerfileError(f"line {number}: unknown instruction {head!r}")
    rest = rest.strip()

    flags: list[tuple[str, str]] = []
    if keyword in _FLAGGED:
        while rest.startswith("--"):
            token, _, rest = rest.partition(" ")
            name, _, value = token[2:].partition("=")
            flags.append((name, value))
            rest = rest.strip()

    if keyword in {"RUN", "COPY", "ADD"} and _HEREDOC.search(rest):
        raise DockerfileError(
            f"line {number}: heredocs (`<<EOF`) are not supported here; write "
            f"the commands as one RUN joined with &&, or put the file in the "
            f"build context and COPY it"
        )

    if keyword in _JSON_CAPABLE and rest.startswith("["):
        parsed = _json_array(rest)
        if parsed is not None:
            return Instruction(
                keyword=keyword,
                form="exec",
                args=parsed,
                flags=tuple(flags),
                line=number,
            )

    if keyword in _COMMAND_LINES:
        if not rest:
            raise DockerfileError(f"line {number}: {keyword} needs a command")
        args: tuple[str, ...] = (rest,)
    else:
        args = tuple(rest.split())
    return Instruction(
        keyword=keyword, form="shell", args=args, flags=tuple(flags), line=number
    )


def _json_array(text: str) -> tuple[str, ...] | None:
    """The array, or `None` when it is not a JSON array of strings.

    `None` rather than an error, because that is what Docker does with it:
    `CMD [python, app.py]` is not JSON, so it is run *through a shell* as the
    literal text, and the container fails at start with `[python,: not found`.
    """
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return tuple(value)


def _assignments(instruction: Instruction) -> dict[str, str]:
    """`ARG NAME=default`, `ENV KEY=value ...` and the legacy `ENV KEY value`."""
    text = " ".join(instruction.args)
    try:
        tokens = shlex.split(text)
    except ValueError as exc:
        raise DockerfileError(f"line {instruction.line}: {exc}") from exc
    if instruction.keyword == "ENV" and tokens and "=" not in tokens[0]:
        return {tokens[0]: " ".join(tokens[1:])}
    values: dict[str, str] = {}
    for token in tokens:
        name, _, value = token.partition("=")
        values[name] = value
    return values


def _substitute(text: str, variables: Mapping[str, str]) -> str:
    """`$VAR`, `${VAR}`, `${VAR:-default}` and `${VAR:+word}`, as Docker reads them."""

    def replace(match: re.Match[str]) -> str:
        name = match.group("braced") or match.group("bare")
        value = variables.get(name, "")
        match match.group("op"):
            case "-":
                return value or match.group("word")
            case "+":
                return match.group("word") if value else ""
            case _:
                return value

    return _VARIABLE.sub(replace, text)
