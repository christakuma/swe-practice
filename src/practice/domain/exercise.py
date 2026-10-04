"""The content aggregate: an exercise and the kind-specific spec it carries.

Composition, not inheritance (PLAN.md §4.2). `Exercise` holds a discriminated
`spec` union rather than being subclassed per kind, so adding a third kind means
adding a spec and a registry entry instead of re-cutting a class hierarchy.

**Phase 14 added the third kind and graded that prediction.** The half about
inheritance held exactly: `SqlDrillSpec` is a dataclass beside the other two,
nothing was subclassed and no class here was re-cut. The half about "a spec and
a registry entry" did not, and `editable_source` below is where it broke. Two
kinds had taught the whole stack to equate *is a kata* with *is solved by
editing a file* — the workbench seed, the solution-file handoff, `practice
solve`, the fallback source and one template branch all asked
`isinstance(spec, KataSpec)` when the question they meant was the second one. A
third file-based kind has to prise those apart, and the honest place to do it is
here, once, rather than in five `isinstance` chains that would each have to grow
a branch. ADR 0019 is the record.

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
    "EditableSource",
    "Exercise",
    "ExerciseFilter",
    "ExerciseKind",
    "ExerciseSpec",
    "GitScenarioSpec",
    "Hint",
    "KataSpec",
    "ParamValue",
    "SqlDrillSpec",
    "editable_source",
    "validate_checks",
]

_CHECK_ID: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ASSERTION_NAME: Final = re.compile(r"^[a-z][a-z0-9_]*$")


class ExerciseKind(StrEnum):
    """Values match the `kind:` field in `exercise.yaml` and the persisted form."""

    KATA = "kata"
    GIT_SCENARIO = "git_scenario"
    SQL_DRILL = "sql_drill"


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
#
# **`float` arrived in Phase 14, and its absence was a real gap rather than a
# deliberate narrowing.** Nothing in the git vocabulary has ever needed one: a
# commit count is an integer, a ref is a string, `include_untracked` is a flag.
# A SQL drill compares literal rows, and four of the eight shipped drills hold a
# money column — so `[[alice, 77.5]]` was rejected by the schema with twenty
# lines of Pydantic union errors, none of which said "no float here".
#
# Widening it loosens nothing, because narrowness was never enforced here: it is
# enforced by the accessors in `checks/evaluation.Params`, each of which refuses
# a value of the wrong shape for the parameter it is reading.
# `Params.integer` still rejects a float, which
# `test_a_float_is_not_accepted_where_an_integer_is_required` holds it to —
# `commit_count {equals: 1.5}` is a typo, not a count.
type ParamValue = str | int | float | bool | tuple[ParamValue, ...]


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


def validate_checks(
    checks: tuple[CheckSpec, ...],
    counter_examples: tuple[CounterExample, ...],
    *,
    subject: str,
) -> None:
    """The invariants every declaratively-graded spec shares. Raises or returns.

    Hoisted out of `GitScenarioSpec` in Phase 14, when `SqlDrillSpec` arrived
    needing the identical four rules. **Deduplicated rather than restated, and
    the reason is the first rule.** A spec whose checks are all advisory passes
    *vacuously* — worse than having no exercise at all — so this is
    correctness-critical code, and two copies of a vacuous-check guard is
    precisely the drift that ends with one kind of exercise silently grading
    nothing (§5.4).

    The derived one-liners — `required_checks`, `check_ids`, `check` — are
    deliberately *not* hoisted with it. They are single comprehensions over a
    tuple each spec already holds, and a function forwarding one of those is the
    abstraction §13 says to delete. Drift in a filter is visible in a verdict;
    drift in a guard is not visible anywhere.

    `subject` is the word the messages use, so a drill is refused in a drill's
    vocabulary rather than being told it is a scenario.
    """
    if not checks:
        raise InvalidValueError(f"a {subject} needs at least one check")

    ids = [check.id for check in checks]
    duplicates = sorted({name for name in ids if ids.count(name) > 1})
    if duplicates:
        raise InvalidValueError(f"duplicate check ids: {', '.join(duplicates)}")

    if not any(check.is_required for check in checks):
        raise InvalidValueError(
            f"a {subject} needs at least one required check, or every attempt "
            f"passes it vacuously"
        )

    known = frozenset(ids)
    for example in counter_examples:
        unknown = sorted(example.expect_failures - known)
        if unknown:
            raise InvalidValueError(
                f"counter-example {example.file!r} expects unknown check(s): "
                f"{', '.join(unknown)}"
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
    reference_failing_commands: int = 0
    """How many of the reference solution's commands are expected to exit non-zero.

    Zero for almost every exercise, and the content suite holds the reference to
    exactly this number — not "at most", which is the whole point. A conflicting
    `git merge`, a `git rebase` that stops partway and a push rejected as
    non-fast-forward all exit 1, and in three Phase 11 scenarios that exit *is*
    the lesson: the exercise starts when the command fails. Before this field the
    suite required every reference line to succeed, so those exercises were
    unauthorable (§16).

    Counting rather than flagging keeps the original guarantee intact. A blanket
    "this reference may fail" would also excuse a mistyped flag or a path that is
    not there, which is the defect the strict check was written to catch; an exact
    count still fails, and still names the line.
    """

    def __post_init__(self) -> None:
        if not self.fixture.strip() or not self.reference.strip():
            raise InvalidValueError("a scenario needs a fixture and a reference")
        validate_checks(self.checks, self.counter_examples, subject="scenario")

        if not self.allowed_commands:
            raise InvalidValueError("a scenario must allow at least one command")
        if self.max_commands < 1:
            raise InvalidValueError("max_commands must be at least 1")
        if self.command_timeout_seconds < 1:
            raise InvalidValueError("command_timeout_seconds must be at least 1")
        if not 0 <= self.reference_failing_commands <= self.max_commands:
            raise InvalidValueError(
                "reference_failing_commands must be between 0 and max_commands"
            )

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


@dataclass(frozen=True, slots=True)
class SqlDrillSpec:
    """Everything needed to seed a database, run one answer, and grade the result.

    The third kind (PLAN.md §5.3, Phase 14), and the one that applies the core
    bet to a second domain: **a drill is graded on the state the database is
    left in and the rows the answer returns, never on the text of the SQL.** Two
    answers that spell the same join differently are the same answer, and the
    ten assertions in `domain/drills/` cannot tell them apart — which is the
    point, not a limitation.

    **`seed` is a sibling of `fixture`, not of `stub`.** It builds the starting
    database the way a git fixture builds the starting repository, and like a
    fixture it is trusted code (§8.1). Unlike a fixture, the solver is *meant*
    to read it — the schema is the question rather than the answer, and a drill
    with a hidden schema would be a riddle — so the provisioner copies it in.
    What the solver edits is `stub`; `reference` stays behind in the content
    directory for the same reason a kata's does: an answer key inside the exam.

    **No `allowed_commands` and no `max_commands`.** A drill has no command
    console, so there is nothing to police — and `AttemptPolicy.for_exercise`
    already encodes that honestly for a kata (a zero budget and an empty
    allowlist), which a drill falls into unchanged. The one place in this phase
    where a third kind cost nothing.

    `statement_timeout_seconds` bounds the whole answer rather than one
    statement of it. A drill's answer is a handful of statements against tens of
    rows, so the only thing this ever catches is a recursive CTE with no base
    case, and what is worth bounding there is the attempt.
    """

    seed: str
    stub: str
    reference: str
    checks: tuple[CheckSpec, ...]
    counter_examples: tuple[CounterExample, ...] = ()
    statement_timeout_seconds: int = 10

    def __post_init__(self) -> None:
        for name, value in (
            ("seed", self.seed),
            ("stub", self.stub),
            ("reference", self.reference),
        ):
            if not value.strip():
                raise InvalidValueError(f"a drill needs a {name}")
        validate_checks(self.checks, self.counter_examples, subject="drill")
        if self.statement_timeout_seconds < 1:
            raise InvalidValueError("statement_timeout_seconds must be at least 1")

    @property
    def kind(self) -> ExerciseKind:
        return ExerciseKind.SQL_DRILL

    @property
    def required_checks(self) -> tuple[CheckSpec, ...]:
        return tuple(check for check in self.checks if check.is_required)

    @property
    def check_ids(self) -> frozenset[str]:
        return frozenset(check.id for check in self.checks)

    @property
    def referenced_files(self) -> tuple[str, ...]:
        """Every sibling file this spec names, relative to the exercise directory.

        All four roles in one list, unlike the other two kinds. A kata lists its
        reference but not its hidden tests as a separate concern; a scenario
        lists its `.cmds` files through `command_lists` as well, because every
        line in them is policed against an allowlist a drill does not have. A
        drill's counter-examples are plain SQL files like its reference, so one
        list covers them.
        """
        return (self.seed, self.stub, self.reference, *self.counter_example_files)

    @property
    def counter_example_files(self) -> tuple[str, ...]:
        return tuple(example.file for example in self.counter_examples)

    def check(self, check_id: str) -> CheckSpec:
        """Look a check up by id, for the counter-example replay in CI."""
        for candidate in self.checks:
            if candidate.id == check_id:
                return candidate
        raise InvalidValueError(f"no such check: {check_id!r}")


type ExerciseSpec = KataSpec | GitScenarioSpec | SqlDrillSpec


@dataclass(frozen=True, slots=True)
class EditableSource:
    """The file a solver edits, its language, and the author's answer to it.

    **The abstraction the third kind forced, and the only thing in Phase 14 that
    was a change rather than an addition.** Before it, five places asked
    `isinstance(spec, KataSpec)` to decide whether an exercise has a text editor
    at all: the workbench's editor seed, the solution-file handoff, `practice
    solve`'s next-step line, the fallback source it reads when no `--source` is
    given, and the template branch that picks a console over a CodeMirror pane.
    Every one of them meant *is there a file to edit*, and for exactly two kinds
    those two questions had the same answer.

    A third file-based kind makes them different, and the two available
    responses were to grow five `isinstance` chains by a branch each, or to name
    the question once. The second is one place to be wrong instead of five, and
    it is total over the union above — so a fourth kind is a clause the type
    checker demands rather than a branch someone has to remember.

    `language` is here rather than derived from the filename extension because
    it is also what the web layer hands CodeMirror as a mode name, and §15 Q3's
    claim is that a second language is a content change plus a vendored mode
    file. A `.sql` → `sql` mapping hidden in a route handler would be a third
    thing to change.

    `reference` is the author's own answer, and it is on this object rather than
    looked up separately because of where it is read: `practice solve
    --reference` grades the reference *through the same path* a solver's file
    takes, which is the mechanism the whole content suite rests on. Both kinds
    that have an editable file have one, and a caller holding this never needs a
    second `isinstance` to find it.
    """

    filename: str
    language: str
    reference: str


def editable_source(spec: ExerciseSpec) -> EditableSource | None:
    """The file this kind is solved by editing, or `None` when there is not one.

    `None` is the answer for a git scenario, and a real answer rather than a
    gap: a scenario's surface is a console over a repository, and what is graded
    is the repository rather than any one file in it.

    Total over `ExerciseSpec` by construction. The final `return None` is
    unreachable for the three kinds that exist, and mypy names it the moment a
    fourth is added without a clause here — which is the property that makes
    this worth having over five scattered tests.
    """
    if isinstance(spec, KataSpec):
        return EditableSource(
            filename=spec.stub, language=spec.language, reference=spec.reference
        )
    if isinstance(spec, SqlDrillSpec):
        return EditableSource(
            filename=spec.stub, language="sql", reference=spec.reference
        )
    return None


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
