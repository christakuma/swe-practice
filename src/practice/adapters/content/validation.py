"""Auditing the exercise library: everything checkable without running anything.

`loader` answers "can this be read as an exercise?". This module answers "is it
a *good* one?" — and the split is the same line PLAN.md §4.2 draws inside the
domain. A correctness hole is a load failure; a quality rule is a report.

**What is deliberately not here, and what has moved.** PLAN.md §9's content
suite has two halves and only the first could land in Phase 2. Phase 3 took a
bite out of the second — `tests/content/test_fixtures.py` runs every fixture and
replays every reference command list through the real sandbox, and `practice
fixtures --check` holds the commit hashes to `content/fixtures.lock` — and Phase
4 took another: `tests/content/test_katas.py` grades every kata's reference
solution and its stub, so the claim that a kata is solvable and that its hidden
suite rejects an empty stub is now tested rather than asserted.

This module still does none of that, on purpose. `validate` runs nothing — it is
the fast, offline audit an author runs while editing, and it has to stay usable
on a machine with no git. What is left genuinely unproven is *scenario* grading:
whether a replayed solution's end state passes every required check, and whether
each counter-example fails exactly the checks it declares, needs the engine in
Phase 5. `unproven_by_design` is that caveat in code, so a passing run says
which guarantees it is not making.

What this module *can* prove is the thing §5.3 was written for: every line of
every reference and counter-example list is legal under the exercise's own
`allowed_commands`. Without it CI would eventually bless a scenario whose
reference solution only works if you are allowed to type something the solver is
not — a green build on an unsolvable exercise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from practice.adapters.content.errors import ContentError
from practice.adapters.content.loader import (
    EXERCISE_FILENAME,
    NOTES_FILENAME,
    load_exercise,
    load_exercise_file,
)
from practice.domain.commands import parse_command_list
from practice.domain.errors import InvalidValueError
from practice.domain.exercise import GitScenarioSpec

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from practice.domain.exercise import Exercise

__all__ = [
    "ExerciseReport",
    "LibraryReport",
    "discover",
    "unproven_by_design",
    "validate_exercise",
    "validate_library",
]

#: How deep an exercise directory sits under the content root: `<track>/<slug>`.
_EXERCISE_DEPTH: Final = 2

#: Directories the walk ignores wholesale. `_lib` holds the shared fixture bash
#: and is not a track.
_IGNORED_PREFIXES: Final = ("_", ".")


def unproven_by_design() -> tuple[str, ...]:
    """The guarantees a Phase 2 validation run does *not* make.

    Printed by `practice validate`. A validation command that reports "3 passed"
    and says nothing else invites exactly the misreading PLAN.md §11 warns
    against, and the warning is worth more in the output than in the plan.
    """
    return (
        (
            "solution.cmds is replayed through the sandbox by the content suite "
            "and `practice fixtures`, but not yet GRADED: whether the end state "
            "passes every required check needs the engine in phase 5"
        ),
        "counter-examples are not yet proven to fail the checks they declare",
    )


@dataclass(frozen=True, slots=True)
class ExerciseReport:
    """What one exercise directory looked like. Empty `problems` means good."""

    directory: Path
    exercise_id: str | None
    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def name(self) -> str:
        """The id when it could be read, the directory when it could not."""
        return self.exercise_id or str(self.directory)


@dataclass(frozen=True, slots=True)
class LibraryReport:
    """Every exercise under one content root, plus the walk's own problems."""

    root: Path
    exercises: tuple[ExerciseReport, ...]
    problems: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.problems and all(report.ok for report in self.exercises)

    @property
    def failures(self) -> tuple[ExerciseReport, ...]:
        return tuple(report for report in self.exercises if not report.ok)


def discover(root: Path) -> Iterator[Path]:
    """Every exercise directory under `root`, in a stable order.

    Walks for `exercise.yaml` at any depth rather than globbing `*/*/` on
    purpose: a file nested one level too deep would otherwise be invisible, and
    "the exercise I added does not appear and nothing says why" is a worse half
    hour than a validation error. `validate_library` reports the misplaced ones.
    """
    for path in sorted(root.rglob(EXERCISE_FILENAME)):
        directory = path.parent
        parts = directory.relative_to(root).parts
        if any(part.startswith(_IGNORED_PREFIXES) for part in parts):
            continue
        yield directory


def validate_library(root: Path) -> LibraryReport:
    """Audit every exercise under a content root."""
    if not root.is_dir():
        return LibraryReport(root=root, exercises=(), problems=("no such directory",))

    directories = []
    problems = []
    for directory in discover(root):
        depth = len(directory.relative_to(root).parts)
        if depth != _EXERCISE_DEPTH:
            located = directory.relative_to(root).as_posix()
            problems.append(
                f"{located}/{EXERCISE_FILENAME}: is {depth} levels below the "
                f"content root; an exercise lives at <track>/<slug>, which is "
                f"{_EXERCISE_DEPTH}"
            )
            continue
        directories.append(directory)

    # An empty library passing silently is the same failure the architecture
    # test guards against with `test_the_walk_actually_found_the_domain`: a
    # checker that found nothing reports success just as loudly as one that
    # checked everything.
    if not directories and not problems:
        problems.append("holds no exercises")

    return LibraryReport(
        root=root,
        exercises=tuple(validate_exercise(directory) for directory in directories),
        problems=tuple(problems),
    )


def validate_exercise(directory: Path) -> ExerciseReport:
    """Audit one exercise directory. Never raises; problems are the return value.

    Returning rather than raising is what lets `practice validate` report every
    broken exercise in one run. Fixing one per invocation to discover the next
    is a bad way to spend an afternoon, and with seventy exercises it stops
    being merely annoying.
    """
    try:
        exercise = load_exercise(directory)
    except ContentError as exc:
        return ExerciseReport(
            directory=directory,
            exercise_id=_best_effort_id(directory),
            problems=tuple(
                f"{EXERCISE_FILENAME}: {problem}" for problem in exc.problems
            ),
        )

    return ExerciseReport(
        directory=directory,
        exercise_id=str(exercise.id),
        problems=tuple(_audit(directory, exercise)),
    )


def _best_effort_id(directory: Path) -> str | None:
    """The id from a file that failed to load, for a readable failure heading."""
    try:
        return str(load_exercise_file(directory / EXERCISE_FILENAME).id)
    except ContentError:
        return None


def _audit(directory: Path, exercise: Exercise) -> Iterator[str]:
    yield from _audit_quality(exercise)
    yield from _audit_referenced_files(directory, exercise)
    if isinstance(exercise.spec, GitScenarioSpec):
        yield from _audit_command_lists(directory, exercise.spec)


def _audit_quality(exercise: Exercise) -> Iterator[str]:
    """The rules about a good exercise that the domain deliberately declines.

    An exercise with no hints and no notes is representable — someone is
    halfway through drafting it — and shipping it is still wrong, because the
    notes are where the *why* lives and the why is the entire product (§9).
    """
    if not exercise.hints:
        yield "has no hints"
    if not exercise.notes.strip():
        yield f"{NOTES_FILENAME}: is missing or empty"


def _audit_referenced_files(directory: Path, exercise: Exercise) -> Iterator[str]:
    for name in exercise.spec.referenced_files:
        if not (directory / name).is_file():
            yield f"{name}: named by the spec but not on disk"


def _audit_command_lists(directory: Path, spec: GitScenarioSpec) -> Iterator[str]:
    """Every reference and counter-example line, against this exercise's policy.

    The PLAN.md §5.3 guarantee, enforced: a reference solution validated through
    an execution path the solver cannot use proves only that *a* solution
    exists, not that one exists within the rules — and a scenario could ship
    literally unsolvable with the build still green.
    """
    for name in spec.command_lists:
        path = directory / name
        if not path.is_file():
            continue  # already reported by the referenced-files audit
        try:
            commands = parse_command_list(path.read_text(encoding="utf-8"))
        except InvalidValueError as exc:
            yield f"{name}: {exc}"
            continue

        if not commands:
            yield f"{name}: holds no commands"
        for command in commands:
            if command.program not in spec.allowed_commands:
                yield (
                    f"{name}: line {command.lineno}: {command.program!r} is not in "
                    f"allowed_commands ({', '.join(sorted(spec.allowed_commands))})"
                )
        if len(commands) > spec.max_commands:
            yield (
                f"{name}: {len(commands)} commands exceeds the exercise's own "
                f"max_commands of {spec.max_commands}"
            )
