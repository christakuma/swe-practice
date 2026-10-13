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

Phase 5 took the last bite: `tests/content/test_scenarios.py` grades every
reference solution and every counter-example through the real use cases, so the
§9 content suite is complete and the caveat this module used to print about
scenario grading is gone.

This module still runs nothing, on purpose. `validate` is the fast, offline audit
an author runs while editing, and it has to stay usable on a machine with no git.
So what is left unproven is no longer a missing engine but a deliberate division
of labour, and `unproven_by_design` says which half a passing run is: an exercise
that validates is well-formed and legal, and whether it is *solvable* is the test
suite's answer, not this command's.

What this module *can* prove is the thing §5.3 was written for: every line of
every reference and counter-example list is legal under the exercise's own
`allowed_commands`. Without it CI would eventually bless a scenario whose
reference solution only works if you are allowed to type something the solver is
not — a green build on an unsolvable exercise.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from practice.adapters.content.curriculum import (
    CURRICULUM_FILENAME,
    load_curriculum,
)
from practice.adapters.content.errors import ContentError
from practice.adapters.content.loader import (
    EXERCISE_FILENAME,
    NOTES_FILENAME,
    load_exercise,
    load_exercise_file,
)
from practice.adapters.content.tracks import TRACKS_FILENAME, load_tracks
from practice.domain.checks import registry as checks
from practice.domain.commands import parse_command_list
from practice.domain.drills import registry as drills
from practice.domain.errors import InvalidValueError
from practice.domain.exercise import GitScenarioSpec, SqlDrillSpec

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
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
    """The guarantees a validation run does *not* make, and never will.

    Printed by `practice validate`. A validation command that reports "3 passed"
    and says nothing else invites exactly the misreading PLAN.md §11 warns
    against, and the warning is worth more in the output than in the plan.

    Both entries used to name Phase 5 as the thing that was missing. Phase 5 has
    landed and the list is shorter and permanent: what remains unproven here is
    unproven *by design*, because this command does not run anything. An author who
    wants to know whether an exercise is solvable runs the test suite, and the
    output says so rather than leaving them to assume a green audit covered it.
    """
    return (
        (
            "nothing here is executed: a fixture that cannot run, a reference "
            "solution that reaches the wrong end state and a counter-example that "
            "fails the wrong checks all pass this audit. `uv run pytest -m content` "
            "is what grades them"
        ),
        (
            "an exercise's prose is not reviewed: a check's label and explanation "
            "are present and non-empty, and nothing can tell you whether they are "
            "true of the assertion they are attached to"
        ),
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

    variants = _variants(directories)
    placed = [directory for directory in directories if directory not in variants]
    problems.extend(_audit_variants(root, directories, variants))
    problems.extend(_audit_curriculum(root, placed))
    problems.extend(_audit_tracks(root, placed))

    return LibraryReport(
        root=root,
        exercises=tuple(validate_exercise(directory) for directory in directories),
        problems=tuple(problems),
    )


def _variants(directories: Sequence[Path]) -> dict[Path, Exercise]:
    """The directories that hold a variant, with the exercise each one loads as.

    A directory that will not load is in neither half: it is reported once, by
    `validate_exercise`, and guessing here whether it *meant* to be a variant
    would report it a second time for a problem it may not have.
    """
    found = {}
    for directory in directories:
        try:
            exercise = load_exercise(directory)
        except ContentError:
            continue
        if exercise.is_variant:
            found[directory] = exercise
    return found


def _audit_variants(
    root: Path, directories: Sequence[Path], variants: dict[Path, Exercise]
) -> Iterator[str]:
    """A variant must be a twist on a real, standard exercise of its own kind.

    Three library-level rules, each a way for a variant to be unreachable or
    absurd, and none of them something one `exercise.yaml` can know:

    * **its base exists** -- a variant of nothing is offered under no exercise,
      so it is on disk, graded by the suite, and never shown to anyone;
    * **its base is not itself a variant** -- `variants_of` goes one level deep,
      so a twist on a twist would be exactly as unreachable;
    * **its base is the same kind** -- a version of a kata that opens a git
      console is not a version of it.

    The other library rule about variants is enforced by subtraction rather
    than here: they are left out of what the curriculum and the tracks must
    name, so a manifest that *does* name one fails as naming something that is
    not there to be placed.
    """
    on_disk = {
        directory.relative_to(root).as_posix(): directory for directory in directories
    }
    for directory, exercise in sorted(variants.items()):
        if exercise.variant is None:  # pragma: no cover -- `_variants` filtered
            continue
        base_id = exercise.variant.of.value
        located = f"{directory.relative_to(root).as_posix()}/{EXERCISE_FILENAME}"
        base_directory = on_disk.get(base_id)
        if base_directory is None:
            yield f"{located}: is a variant of {base_id}, which is not in the library"
            continue
        if base_directory in variants:
            yield (
                f"{located}: is a variant of {base_id}, which is itself a variant; "
                f"a twist is on a standard exercise"
            )
            continue
        try:
            base = load_exercise(base_directory)
        except ContentError:
            continue
        if base.kind is not exercise.kind:
            yield (
                f"{located}: is a {exercise.kind.value} and a variant of {base_id}, "
                f"which is a {base.kind.value}"
            )


def _audit_curriculum(root: Path, directories: Sequence[Path]) -> Iterator[str]:
    """The manifest must name every exercise exactly once and nothing else.

    A library-level rule rather than a per-exercise one, because no single
    exercise can fail it: "listed twice" and "not listed" are both statements
    about the whole file.

    **This is what stops the manifest rotting.** An ordering that silently omits
    the exercise someone added last week is worse than no ordering, because it
    looks deliberate — the new exercise appears at the end of the library and
    nothing anywhere says it was never placed. Phase 11 added fifty-one
    exercises; an unchecked manifest would have been wrong within a week.
    """
    if not directories:
        return
    try:
        curriculum = load_curriculum(root)
    except ContentError as exc:
        yield from (f"{CURRICULUM_FILENAME}: {problem}" for problem in exc.problems)
        return

    listed = curriculum.exercise_ids
    on_disk = {directory.relative_to(root).as_posix() for directory in directories}
    named = [str(exercise_id) for exercise_id in listed]

    repeated = sorted({name for name in named if named.count(name) > 1})
    if repeated:
        yield f"{CURRICULUM_FILENAME}: lists twice: {', '.join(repeated)}"

    missing = sorted(on_disk - set(named))
    if missing:
        yield f"{CURRICULUM_FILENAME}: does not list: {', '.join(missing)}"

    unknown = sorted(set(named) - on_disk)
    if unknown:
        yield (
            f"{CURRICULUM_FILENAME}: lists exercise(s) that are not on disk: "
            f"{', '.join(unknown)}"
        )


def _audit_tracks(root: Path, directories: Sequence[Path]) -> Iterator[str]:
    """A track may only name exercises that exist, in an order the curriculum
    does not contradict.

    **The second rule is what the word *sensible* is resting on.** A track is
    free to select and free to put the curriculum's sections in an order of its
    own -- the Blind 75 meets the two-pointer katas before the string ones, and
    the git track meets recovery before collaboration. What it may not do is
    reverse two exercises *inside one section*, because that is the order ADR
    0014 says is dependency: `is-it-a-subtree` reuses the comparison
    `are-two-trees-the-same` establishes, and a track that offered them the
    other way round would be offering a lesson before its premise.

    So the dependency argument is made once, in `curriculum.yaml`, and every
    track is held to it. Somebody who reorders a section for a reason gets a
    failure naming each track that still has the old order, instead of a track
    that silently kept teaching it backwards.

    Nothing is said when the file is absent: a library may decline to offer
    tracks. A track that follows the curriculum cannot break either rule, so it
    is not examined.
    """
    if not directories:
        return
    try:
        declarations = load_tracks(root)
    except ContentError as exc:
        yield from (f"{TRACKS_FILENAME}: {problem}" for problem in exc.problems)
        return

    on_disk = {directory.relative_to(root).as_posix() for directory in directories}
    try:
        sections = load_curriculum(root).tracks
    except ContentError:
        # Already reported by `_audit_curriculum`, and without an order there is
        # nothing to hold a track's order against.
        sections = ()

    for declaration in declarations:
        if declaration.exercises is None:
            continue
        unknown = sorted(
            exercise_id.value
            for exercise_id in declaration.exercises
            if exercise_id.value not in on_disk
        )
        if unknown:
            yield (
                f"{TRACKS_FILENAME}: {declaration.name}: lists exercise(s) that "
                f"are not on disk: {', '.join(unknown)}"
            )
        placed = {
            exercise_id: index
            for index, exercise_id in enumerate(declaration.exercises)
        }
        for section in sections:
            shared = [found for found in section.exercises if found in placed]
            for earlier, later in itertools.pairwise(shared):
                if placed[earlier] > placed[later]:
                    yield (
                        f"{TRACKS_FILENAME}: {declaration.name}: puts {later} "
                        f"before {earlier}, and {CURRICULUM_FILENAME} orders "
                        f"them the other way inside '{section.name}'"
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
    yield from _audit_something_is_graded(exercise)
    if isinstance(exercise.spec, GitScenarioSpec):
        yield from _audit_command_lists(directory, exercise.spec)


def _audit_something_is_graded(exercise: Exercise) -> Iterator[str]:
    """Every declaratively-graded exercise must require at least one *state* check.

    **A rule the third kind made visible rather than one it needed.** The domain
    already refuses a spec whose checks are all advisory, because that passes
    vacuously (§5.4). This is the narrower hole that guard leaves open: an
    exercise whose only *required* check reads the solver's text rather than any
    state. For a drill that is a required `sql_matches`; for a scenario it is a
    required `command_used`. Both would pass an answer that is wrong and mentions
    the right keyword, which is precisely the string matching
    [ADR 0003](../../../../docs/adr/0003-grade-git-exercises-by-repo-state.md)
    was written to reject — reintroduced through the back door, one `severity:`
    at a time.

    **Checked for both kinds, not just the new one.** The hole had been open on
    the git side since Phase 5 and nothing had fallen into it: the 24 scenarios
    all require a ref, a tree or a worktree check, and `command_used` is advisory
    in every one of them. Writing the rule for drills alone would have been
    writing down a standard the older half of the library was meeting by habit.

    Here rather than in the domain, and the reason is the line `exercise.py`
    draws. A spec that requires only a craft check is *representable* — somebody
    is halfway through drafting one, with the state checks still to write — and
    the domain refusing it would refuse the draft. What must not happen is
    shipping it, and `practice validate` is the thing that runs in CI.
    """
    spec = exercise.spec
    if isinstance(spec, GitScenarioSpec):
        state = checks.CONTENT_ASSERTIONS
        craft = "command_used"
    elif isinstance(spec, SqlDrillSpec):
        state = drills.STATE_ASSERTIONS
        craft = "sql_matches / query_plan_matches"
    else:
        # A kata's checks come out of its test suite rather than its spec, so
        # there is nothing declared here to audit. `tests/content/test_katas.py`
        # holds the equivalent claim by grading the stub and requiring it to
        # fail.
        return

    required = [check for check in spec.checks if check.is_required]
    if not any(check.assertion in state for check in required):
        yield (
            f"requires no check that reads state: every required check is a "
            f"craft assertion ({craft}), so a wrong answer that mentions the "
            f"right keyword would pass"
        )


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
