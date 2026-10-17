"""`BuildQuery` over a workspace directory: the real implementation.

Reads the build context from disk and the editable file from the attempt, and
answers every port question from the parsed result. **The editable file comes
from the attempt rather than from the directory** because a verdict is derived
from a source the attempt remembers (the rule `SqlDrillGrader` and
`KataGrader` state). In own-editor mode the two are the same file anyway; in
the browser the disk copy is whatever was provisioned.

**`path_in_image` tracks where each context file lands, not only whether it
was copied**, because the multi-stage answer to the secrets lesson depends on
it. A builder stage that runs `COPY . .` holds `.env`. A final stage that runs
`COPY --from=build /app/dist /app` does not, and only by following the path
through `/app` can the query tell those apart rather than failing the right
answer. A `COPY --from=` an image outside this file copies nothing from the
context, so it adds nothing here.
"""

from __future__ import annotations

import posixpath
import re
import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from practice.adapters.container.compose import ComposeError, parse_compose
from practice.adapters.container.dockerfile import (
    DockerfileError,
    compose_process,
    lineage,
    parse,
    stage_index,
)
from practice.adapters.container.dockerignore import (
    IgnoreRules,
    glob_matcher,
    normalise_path,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

    from practice.domain.ports import Instruction, Stage

__all__ = ["ParsedBuildQuery", "context_files"]

DOCKERFILE: Final = "Dockerfile"
COMPOSE_FILE: Final = "compose.yaml"
_GLOB: Final = frozenset("*?[")

#: A context file and where in a stage's filesystem it ended up.
type Landing = tuple[str, str]


class ParsedBuildQuery:
    """Satisfies `practice.domain.ports.BuildQuery` over a directory on disk."""

    __slots__ = ("_compose", "_error", "_files", "_stages")

    def __init__(
        self,
        *,
        context: Mapping[str, str],
        editable: str,
        source: str,
    ) -> None:
        """`context` maps every build-context path to its text; `source` overrides one.

        A mapping rather than a directory, so the conformance suite and the
        grader read the same way, and so this class never touches a path.
        """
        files = dict(context)
        files[editable] = source
        ignore = IgnoreRules(files.get(".dockerignore", ""))
        self._files = ignore.kept(sorted(files))
        self._stages: tuple[Stage, ...] = ()
        self._compose: dict[str, dict[str, object]] = {}
        self._error: str | None = None
        try:
            if DOCKERFILE in files:
                self._stages = parse(files[DOCKERFILE])
            if COMPOSE_FILE in files:
                self._compose = parse_compose(files[COMPOSE_FILE])
        except (DockerfileError, ComposeError) as exc:
            self._error = str(exc)

    def error(self) -> str | None:
        return self._error

    def stages(self) -> tuple[Stage, ...]:
        return self._stages

    def effective_process(self) -> tuple[str, ...]:
        return compose_process(self._stages)

    def final_user(self) -> str:
        return lineage(self._stages).user if self._stages else "root"

    def path_in_image(self, path: str) -> bool:
        if not self._stages:
            return False
        wanted = normalise_path(path)
        shipped = _landings(self._stages, self._files)[-1].layers
        return any(source == wanted for source, _ in shipped)

    def services(self) -> frozenset[str]:
        return frozenset(self._compose)

    def service(self, name: str) -> Mapping[str, object] | None:
        return self._compose.get(name)


def context_files(root: Path) -> dict[str, str]:
    """Every file under `root`, by slash-separated relative path, as text.

    Undecodable bytes are replaced rather than refused: a context may hold a
    binary asset, and the query only ever needs its *name*.
    """
    return {
        path.relative_to(root).as_posix(): path.read_text(
            encoding="utf-8", errors="replace"
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@dataclass(frozen=True, slots=True)
class _Held:
    """What one stage holds, two ways, because Docker answers two questions.

    `layers` is every context file ever written into one of the stage's layers,
    and it only grows. That is what ships, and why `RUN rm .env` does not help:
    the layer that copied the file still has it. `visible` is the stage's
    filesystem at its end, with removed files gone, and it is what `COPY
    --from=<stage>` copies. The difference is the multi-stage answer to the
    secrets exercise, where a builder that copied and deleted `.env` hands a
    final stage nothing.
    """

    layers: frozenset[Landing]
    visible: frozenset[Landing]
    workdir: str


def _landings(stages: Sequence[Stage], files: Sequence[str]) -> list[_Held]:
    """For every stage, which context files it holds and where."""
    results: list[_Held] = []
    for index, stage in enumerate(stages):
        parent = stage_index(stages[:index], stage.base)
        inherited = results[parent] if parent is not None else None
        layers = set(inherited.layers) if inherited else set()
        visible = set(inherited.visible) if inherited else set()
        workdir = inherited.workdir if inherited else "/"
        for instruction in stage.instructions:
            added: set[Landing] = set()
            if instruction.keyword == "WORKDIR" and instruction.args:
                workdir = posixpath.normpath(
                    posixpath.join(workdir, instruction.args[0])
                )
            elif instruction.keyword in {"COPY", "ADD"} and instruction.args[1:]:
                source_stage = dict(instruction.flags).get("from")
                if source_stage is None:
                    added = _from_context(instruction, files, workdir)
                else:
                    origin = stage_index(stages[:index], source_stage)
                    if origin is not None:
                        added = _from_stage(
                            instruction, results[origin].visible, workdir
                        )
            elif instruction.keyword == "RUN" and instruction.form == "shell":
                removed = _removed(instruction.args[0], workdir)
                visible = {
                    landing for landing in visible if not _under(landing[1], removed)
                }
            layers |= added
            visible |= added
        results.append(
            _Held(layers=frozenset(layers), visible=frozenset(visible), workdir=workdir)
        )
    return results


def _removed(line: str, workdir: str) -> tuple[str, ...]:
    """The paths an `rm` in a shell-form `RUN` deletes, resolved against `WORKDIR`.

    Reads `rm` commands joined by `&&` or `;` and nothing cleverer. A deletion
    it cannot see leaves the file visible, which errs towards reporting a leak
    that a `COPY --from` would not really carry. That is the conservative
    direction for a check whose job is keeping a secret out.
    """
    targets: list[str] = []
    for command in re.split(r"&&|;", line):
        try:
            words = shlex.split(command)
        except ValueError:
            continue
        if not words or words[0] != "rm":
            continue
        for word in words[1:]:
            if not word.startswith("-"):
                targets.append(posixpath.normpath(posixpath.join(workdir, word)))
    return tuple(targets)


def _under(spot: str, removed: Sequence[str]) -> bool:
    return any(spot == target or spot.startswith(target + "/") for target in removed)


def _from_context(
    instruction: Instruction, files: Sequence[str], workdir: str
) -> set[Landing]:
    *sources, dest = instruction.args
    target = posixpath.normpath(posixpath.join(workdir, dest))
    into_directory = dest.endswith("/") or len(sources) > 1
    landed: set[Landing] = set()
    for raw in sources:
        source = normalise_path(raw)
        source = "" if source == "." else source
        # Docker's matcher, not `fnmatch`: `*` stops at a slash, so `*.py` copies
        # the top-level modules and not `pkg/models.py`. `fnmatch` lets `*`
        # cross directories, and the first version of this reported files in
        # the image that a real build leaves out.
        glob = glob_matcher(source) if _GLOB & set(source) else None
        for path in files:
            if not source:
                landed.add((path, posixpath.join(target, path)))
            elif path == source or (glob is not None and glob.fullmatch(path)):
                name = posixpath.basename(path)
                spot = (
                    posixpath.join(target, name)
                    if into_directory or glob is not None
                    else target
                )
                landed.add((path, spot))
            elif path.startswith(source + "/"):
                landed.add((path, posixpath.join(target, path[len(source) + 1 :])))
    return landed


def _from_stage(
    instruction: Instruction, held: Iterable[Landing], workdir: str
) -> set[Landing]:
    *sources, dest = instruction.args
    target = posixpath.normpath(posixpath.join(workdir, dest))
    landed: set[Landing] = set()
    for raw in sources:
        source = posixpath.join("/", raw).rstrip("/") or "/"
        for origin, spot in held:
            if spot == source:
                name = posixpath.basename(spot)
                landed.add(
                    (
                        origin,
                        posixpath.join(target, name) if dest.endswith("/") else target,
                    )
                )
            elif source == "/" or spot.startswith(source + "/"):
                landed.add(
                    (origin, posixpath.join(target, spot[len(source) :].lstrip("/")))
                )
    return landed
