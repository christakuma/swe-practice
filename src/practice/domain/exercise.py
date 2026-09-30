"""The content aggregate: an exercise and the kind-specific spec it carries.

Composition, not inheritance (PLAN.md §4.2). `Exercise` holds a discriminated
`spec` union rather than being subclassed per kind, so adding a third kind means
adding a spec and a registry entry instead of re-cutting a class hierarchy.

Two invariants live here rather than in the Phase 2 schema layer, and the line
between them is worth stating because it is not arbitrary:

* **Correctness holes are domain invariants.** A scenario whose checks are all
  advisory *passes vacuously* — worse than having no exercise at all — so
  `GitScenarioSpec` refuses to exist without a required check. Likewise a
  counter-example naming a check id that does not exist can never fail the check
  it claims to.
* **Quality rules stay in the content suite.** "Hints and notes are non-empty" is
  a rule about a good exercise, not about a representable one, and the domain
  should not refuse to model an exercise someone is halfway through drafting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from practice.domain.errors import InvalidValueError
from practice.domain.verdict import Severity

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.domain.ids import ExerciseId, Tag

__all__ = [
    "CheckSpec",
    "ComplexityExpectation",
    "CounterExample",
    "Difficulty",
    "Exercise",
    "ExerciseFilter",
    "ExerciseKind",
    "ExerciseSpec",
    "GitScenarioSpec",
    "Hint",
    "KataSpec",
    "ParamValue",
]

_CHECK_ID: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ASSERTION_NAME: Final = re.compile(r"^[a-z][a-z0-9_]*$")


class ExerciseKind(StrEnum):
    """Values match the `kind:` field in `exercise.yaml` and the persisted form."""

    KATA = "kata"
    GIT_SCENARIO = "git_scenario"


class Difficulty(StrEnum):
    """Values match the `difficulty:` field in `exercise.yaml`."""

    INTRO = "intro"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass(frozen=True, slots=True)
class Hint:
    """One progressive hint. Ordering is positional, held by the exercise."""

    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise InvalidValueError("a hint cannot be empty")


@dataclass(frozen=True, slots=True)
class ComplexityExpectation:
    """What the author says a good solution costs.

    Never auto-graded — static Big-O analysis of arbitrary code is not something
    to pretend to do. It is compared against the solver's own claim so that a
    disagreement has to be reconciled by a human (PLAN.md §7).
    """

    expected_time: str
    expected_space: str

    def __post_init__(self) -> None:
        if not self.expected_time.strip() or not self.expected_space.strip():
            raise InvalidValueError("complexity expectations cannot be empty")


# The `with:` mapping in YAML. Recursive because a handful of assertions take a
# list of paths; deliberately narrow, so a check function can exhaust the cases
# instead of casting away from `object`.
type ParamValue = str | int | bool | tuple[ParamValue, ...]


@dataclass(frozen=True, slots=True)
class CheckSpec:
    """One declarative assertion, straight out of the exercise's `checks:` list.

    Field names differ from the YAML keys in exactly two places, both because the
    YAML key is a Python keyword: `assert:` becomes `assertion` and `not:` becomes
    `negated`. Negation is a modifier on every assertion rather than a set of
    paired opposites — one mechanism, and no guessing whether a given assertion
    has a negative twin (PLAN.md §6.3).
    """

    id: str
    label: str
    severity: Severity
    assertion: str
    params: Mapping[str, ParamValue] = field(default_factory=dict)
    negated: bool = False
    explanation: str | None = None

    def __post_init__(self) -> None:
        if not _CHECK_ID.match(self.id):
            raise InvalidValueError(
                f"check id must be lowercase kebab-case, got {self.id!r}"
            )
        if not self.label.strip():
            raise InvalidValueError(f"check {self.id!r} has no label")
        if not _ASSERTION_NAME.match(self.assertion):
            raise InvalidValueError(
                f"check {self.id!r} names an assertion {self.assertion!r}, which is "
                f"not a valid registry key"
            )
        # A read-only view, so a caller that kept a reference to the dict it
        # passed in cannot mutate a check spec after the fact.
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))

    @property
    def is_required(self) -> bool:
        return self.severity is Severity.REQUIRED


@dataclass(frozen=True, slots=True)
class KataSpec:
    """The kata engine's inputs.

    Filenames are relative to the exercise directory; resolving them is the
    content adapter's job, so the domain never holds a filesystem path.
    """

    language: str
    stub: str
    tests: str
    reference: str
    time_limit_seconds: int = 10
    complexity: ComplexityExpectation | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("language", self.language),
            ("stub", self.stub),
            ("tests", self.tests),
            ("reference", self.reference),
        ):
            if not value.strip():
                raise InvalidValueError(f"kata spec needs a {name}")
        if self.time_limit_seconds < 1:
            raise InvalidValueError("time_limit_seconds must be at least 1")

    @property
    def kind(self) -> ExerciseKind:
        return ExerciseKind.KATA

    @property
    def referenced_files(self) -> tuple[str, ...]:
        """Every sibling file this spec names, relative to the exercise directory.

        Here rather than only in the content adapter because two other callers
        want the same list for different reasons: validation checks the files
        exist, and the Phase 3 provisioner copies them into a workspace. A spec
        that names a file the provisioner does not know to copy is the kind of
        disagreement one list avoids.
        """
        return (self.stub, self.tests, self.reference)


@dataclass(frozen=True, slots=True)
class CounterExample:
    """A plausible wrong answer, with the checks it is required to fail.

    "Fails at least one check" is too weak a contract: a counter-example that
    refers to a reflog index depends on a position that shifts when a command is
    added, so an edit could leave it failing for an unrelated reason — or passing
    outright — with CI none the wiser. Naming the expected failures turns that rot
    into a build error (PLAN.md §5.4).
    """

    file: str
    expect_failures: frozenset[str]

    def __post_init__(self) -> None:
        if not self.file.strip():
            raise InvalidValueError("a counter-example needs a file")
        if not self.expect_failures:
            raise InvalidValueError(
                f"counter-example {self.file!r} must declare at least one check it "
                f"is expected to fail"
            )


@dataclass(frozen=True, slots=True)
class GitScenarioSpec:
    """Everything needed to provision, police, and grade a git scenario."""

    fixture: str
    reference: str
    checks: tuple[CheckSpec, ...]
    allowed_commands: frozenset[str]
    counter_examples: tuple[CounterExample, ...] = ()
    max_commands: int = 25
    command_timeout_seconds: int = 10

    def __post_init__(self) -> None:
        if not self.fixture.strip() or not self.reference.strip():
            raise InvalidValueError("a scenario needs a fixture and a reference")
        if not self.checks:
            raise InvalidValueError("a scenario needs at least one check")

        ids = [check.id for check in self.checks]
        duplicates = sorted({name for name in ids if ids.count(name) > 1})
        if duplicates:
            raise InvalidValueError(f"duplicate check ids: {', '.join(duplicates)}")

        if not any(check.is_required for check in self.checks):
            raise InvalidValueError(
                "a scenario needs at least one required check, or every attempt "
                "passes it vacuously"
            )

        known = frozenset(ids)
        for example in self.counter_examples:
            unknown = sorted(example.expect_failures - known)
            if unknown:
                raise InvalidValueError(
                    f"counter-example {example.file!r} expects unknown check(s): "
                    f"{', '.join(unknown)}"
                )

        if not self.allowed_commands:
            raise InvalidValueError("a scenario must allow at least one command")
        if self.max_commands < 1:
            raise InvalidValueError("max_commands must be at least 1")
        if self.command_timeout_seconds < 1:
            raise InvalidValueError("command_timeout_seconds must be at least 1")

    @property
    def kind(self) -> ExerciseKind:
        return ExerciseKind.GIT_SCENARIO

    @property
    def required_checks(self) -> tuple[CheckSpec, ...]:
        return tuple(check for check in self.checks if check.is_required)

    @property
    def check_ids(self) -> frozenset[str]:
        return frozenset(check.id for check in self.checks)

    @property
    def referenced_files(self) -> tuple[str, ...]:
        """Every sibling file this spec names, relative to the exercise directory."""
        return (self.fixture, *self.command_lists)

    @property
    def command_lists(self) -> tuple[str, ...]:
        """The `.cmds` files whose every line must satisfy `allowed_commands`.

        The reference first, then the counter-examples, which is the order a
        validation report reads best in — the solution is the one an author
        looks at first when something is wrong.
        """
        return (self.reference, *(example.file for example in self.counter_examples))

    def check(self, check_id: str) -> CheckSpec:
        """Look a check up by id, for the counter-example replay in CI."""
        for candidate in self.checks:
            if candidate.id == check_id:
                return candidate
        raise InvalidValueError(f"no such check: {check_id!r}")


type ExerciseSpec = KataSpec | GitScenarioSpec


@dataclass(frozen=True, slots=True)
class Exercise:
    """Common metadata plus the kind-specific spec.

    Immutable: content is read from disk and never edited through the domain.
    """

    id: ExerciseId
    kind: ExerciseKind
    title: str
    prompt: str
    difficulty: Difficulty
    tags: tuple[Tag, ...]
    estimated_minutes: int
    hints: tuple[Hint, ...]
    notes: str
    spec: ExerciseSpec

    def __post_init__(self) -> None:
        # `kind` is redundant with `spec.kind` and kept anyway, because the YAML
        # carries it and a loader that silently ignored a mismatch would build an
        # exercise the kind registry then dispatches to the wrong engine.
        if self.kind is not self.spec.kind:
            raise InvalidValueError(
                f"exercise {self.id} declares kind {self.kind.value!r} but carries a "
                f"{self.spec.kind.value!r} spec"
            )
        if not self.title.strip():
            raise InvalidValueError(f"exercise {self.id} has no title")
        if not self.prompt.strip():
            raise InvalidValueError(f"exercise {self.id} has no prompt")
        if self.estimated_minutes < 1:
            raise InvalidValueError(
                f"exercise {self.id} must be estimated at a minute or more"
            )
        if len(set(self.tags)) != len(self.tags):
            raise InvalidValueError(f"exercise {self.id} repeats a tag")

    @property
    def hint_count(self) -> int:
        return len(self.hints)


@dataclass(frozen=True, slots=True)
class ExerciseFilter:
    """Browse criteria. An empty set means "no constraint on this dimension".

    Lives in the domain and does the matching itself so that the filesystem
    repository and any in-memory fake cannot disagree about what a filter means —
    which is exactly the drift that stops a fake being evidence of anything.
    """

    kinds: frozenset[ExerciseKind] = frozenset()
    difficulties: frozenset[Difficulty] = frozenset()
    tags: frozenset[Tag] = frozenset()

    def matches(self, exercise: Exercise) -> bool:
        """Tags match on intersection — any one of them, not all of them."""
        if self.kinds and exercise.kind not in self.kinds:
            return False
        if self.difficulties and exercise.difficulty not in self.difficulties:
            return False
        return not (self.tags and self.tags.isdisjoint(exercise.tags))
