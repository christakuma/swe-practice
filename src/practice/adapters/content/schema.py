"""What a valid `exercise.yaml` looks like, as Pydantic v2 models.

Three rules shape this module, and each of them is a decision rather than a
default.

**Unknown keys are errors.** `extra="forbid"` throughout, so `dificulty: medium`
fails loudly instead of silently taking the default. Silently ignoring a key the
author clearly meant is the most expensive kind of content bug, because the
exercise still loads and still grades — just not the way it was written.

**Nothing here restates a rule the domain already holds.** Not only for the
usual reason — two copies drift — but because a Pydantic constraint that
duplicates a domain invariant makes error messages *worse*. `checks` carried a
`min_length=1` alongside `GitScenarioSpec`'s own "a scenario needs at least one
check": a single mistyped assertion then dropped that check from the tuple and
reported two errors, the real one and "Tuple should have at least 1 item after
validation, not 0". An author reads the second and goes looking for a second
bug that does not exist.

**Domain value objects are constructed inside validators.** `InvalidValueError`
subclasses `ValueError` precisely so that Pydantic turns it into a validation
error with the field path attached (PLAN.md §4.1). That is what keeps the rules
in one place: this module does not restate "an exercise id is `<track>/<slug>`",
it calls `ExerciseId` and lets the domain say so.

**The union is discriminated on `kind`, not on the spec key.** PLAN.md §5.1 and
§5.2 put the kind-specific block under `kata:` and `scenario:` respectively, so
this is not one polymorphic field. Tagging on `kind` means a file that says
`kind: kata` and carries a `scenario:` block is rejected by the discriminator
and by `extra="forbid"`, rather than by a hand-written cross-field check that
has to be kept in step with the union.

**The check vocabulary is per kind as of Phase 14, which is the one place the
third kind changed a rule here rather than extending one.** `CheckModel`
validated `assert:` against a single registry, because there was one. There are
now two deliberately disjoint ones (`domain/drills/registry.py` has the
argument), so the model is split: `CheckModel` validates a scenario's names and
`DrillCheckModel` a drill's. A shared base with the family as a class attribute
is what makes each subclass one line, and what keeps the error message — the
reason any of this is here — written once.

That error message does two things a single registry could not. A name in
neither vocabulary gets the trigram suggestion it always got, over the right
vocabulary. A name in the *other* vocabulary gets told so outright, because
`tree_equals` in a drill is not a typo and no similarity score will find it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    TypeAdapter,
    field_validator,
    model_validator,
)

from practice.domain.checks import registry
from practice.domain.drills import registry as drills
from practice.domain.exercise import (
    CheckSpec,
    ComplexityExpectation,
    CounterExample,
    Difficulty,
    Exercise,
    ExerciseKind,
    ExerciseSpec,
    GitScenarioSpec,
    Hint,
    KataSpec,
    ParamValue,
    SqlDrillSpec,
)
from practice.domain.ids import ExerciseId, tag
from practice.domain.verdict import Severity

# `Mapping`, `ParamValue` and `ExerciseSpec` are imported at runtime rather than
# behind `TYPE_CHECKING`: Pydantic resolves annotations when it builds a model,
# and a name it cannot see leaves the schema half-built with an error that points
# at the type adapter instead of at the missing import.

__all__ = [
    "EXERCISE_FILE",
    "SCHEMA_VERSION",
    "CheckModel",
    "ComplexityModel",
    "CounterExampleModel",
    "DrillCheckModel",
    "ExerciseFile",
    "GitScenarioFile",
    "GitScenarioSpecModel",
    "KataFile",
    "KataSpecModel",
    "SqlDrillFile",
    "SqlDrillSpecModel",
]

#: Bumped only for a change that would make an existing file load *incorrectly*
#: rather than fail to load. `Literal` rather than a range check, so a file from
#: a future version is refused by the schema instead of misread by it.
SCHEMA_VERSION = 1


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


#: Non-empty once whitespace is discounted. Used for every human-readable
#: string, because `title: ""` is a file someone forgot to finish. A validator
#: rather than `Field(pattern=r"\S")`, which is the same rule and reports it as
#: `String should match pattern '\S'` — correct, and no help to an author.
_Text = Annotated[str, AfterValidator(_not_blank)]


class _Model(BaseModel):
    """Shared configuration. Frozen, because content is read and never edited."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )


# --- checks ----------------------------------------------------------------


class _CheckModel(_Model):
    """One entry in a `checks:` list, for whichever vocabulary the kind uses.

    Two field names differ from their YAML keys, both because the key is a Python
    keyword: `assert:` and `not:`. `populate_by_name` means the Python names work
    as well, which is what makes these models constructible in a test without
    writing out a dict of aliases.

    Subclasses supply the vocabulary and nothing else. The validator below is
    the whole reason this base exists: the message it produces is the thing an
    author reads when they get an assertion name wrong, and two copies of it
    would be two chances for one of them to stop suggesting anything.
    """

    id: _Text
    label: _Text
    severity: Severity
    assertion: _Text = Field(alias="assert")
    params: Mapping[str, ParamValue] = Field(default_factory=dict, alias="with")
    negated: bool = Field(default=False, alias="not")
    explanation: str | None = None

    @classmethod
    def _is_registered(cls, value: str) -> bool:
        raise NotImplementedError

    @classmethod
    def _suggest(cls, value: str) -> tuple[str, ...]:
        raise NotImplementedError

    @classmethod
    def _other_family(cls, value: str) -> str | None:
        raise NotImplementedError

    @field_validator("assertion")
    @classmethod
    def _must_be_registered(cls, value: str) -> str:
        """A typo here is a check that never runs, so it is a build failure.

        Without this the exercise still loads and still grades — just with one
        fewer constraint than its author wrote, and nothing says so (§5.4).

        Three outcomes rather than two, as of Phase 14. A registered name
        passes. A name that belongs to the *other* kind's vocabulary is named as
        such, because it is a known fact and no similarity score would find it —
        `tree_equals` and `table_matches` share almost no trigrams. Anything else
        is a typo and gets the suggestion.
        """
        if cls._is_registered(value):
            return value

        family = cls._other_family(value)
        if family is not None:
            raise ValueError(
                f"{value!r} is a {family} assertion, so it cannot be used here; "
                f"this kind's checks read a different port"
            )

        suggestions = cls._suggest(value)
        hint = f"; did you mean {' or '.join(suggestions)}?" if suggestions else ""
        raise ValueError(f"unknown assertion {value!r}{hint}")

    _domain: CheckSpec = PrivateAttr()

    @model_validator(mode="after")
    def _build_domain(self) -> Self:
        """Same reason as `_SpecModel`: `CheckSpec` enforces the kebab-case id
        and the assertion-name shape, and building it here is what puts those
        failures at `checks.3` rather than at the whole `scenario` block.
        """
        self._domain = self.to_domain()
        return self

    @property
    def domain(self) -> CheckSpec:
        return self._domain

    def to_domain(self) -> CheckSpec:
        return CheckSpec(
            id=self.id,
            label=self.label,
            severity=self.severity,
            assertion=self.assertion,
            params=self.params,
            negated=self.negated,
            explanation=self.explanation,
        )


class CheckModel(_CheckModel):
    """One entry in a scenario's `checks:` list: the `RepoQuery` vocabulary."""

    @classmethod
    def _is_registered(cls, value: str) -> bool:
        return registry.is_registered(value)

    @classmethod
    def _suggest(cls, value: str) -> tuple[str, ...]:
        return registry.suggest(value)

    @classmethod
    def _other_family(cls, value: str) -> str | None:
        return drills.misplaced_in_scenario(value)


class DrillCheckModel(_CheckModel):
    """One entry in a drill's `checks:` list: the `DrillQuery` vocabulary."""

    @classmethod
    def _is_registered(cls, value: str) -> bool:
        return drills.is_registered(value)

    @classmethod
    def _suggest(cls, value: str) -> tuple[str, ...]:
        return drills.suggest(value)

    @classmethod
    def _other_family(cls, value: str) -> str | None:
        return drills.other_family(value)


class CounterExampleModel(_Model):
    """A plausible wrong answer and the checks it is required to fail.

    The short form from PLAN.md §5.2 — `counter_examples: [naive.cmds]` — is not
    accepted. §5.4 supersedes it: "fails at least one check" is too weak a
    contract, because a counter-example that references a reflog index can start
    failing for an unrelated reason, or stop failing at all, with CI none the
    wiser. A bare string here is a validation error, not a shorthand.
    """

    file: _Text
    expect_failures: tuple[_Text, ...]

    def to_domain(self) -> CounterExample:
        return CounterExample(
            file=self.file, expect_failures=frozenset(self.expect_failures)
        )


# --- specs -----------------------------------------------------------------


class ComplexityModel(_Model):
    """What the author says a good solution costs. Never auto-graded (§7)."""

    expected_time: _Text
    expected_space: _Text

    def to_domain(self) -> ComplexityExpectation:
        return ComplexityExpectation(
            expected_time=self.expected_time, expected_space=self.expected_space
        )


class _SpecModel(_Model):
    """Base for the two kind-specific blocks.

    The domain spec is built *during* validation and cached, rather than on
    demand afterwards. That is the whole reason this base exists: it gets a
    domain invariant — "a scenario needs at least one required check" — reported
    as a validation error located at `scenario`, instead of escaping later as a
    bare exception from a file that validation already called good.
    """

    _domain: ExerciseSpec = PrivateAttr()

    @model_validator(mode="after")
    def _build_domain(self) -> Self:
        self._domain = self.to_domain()
        return self

    @property
    def domain(self) -> ExerciseSpec:
        return self._domain

    def to_domain(self) -> ExerciseSpec:
        raise NotImplementedError


class KataSpecModel(_SpecModel):
    """The `kata:` block. Filenames are relative to the exercise directory."""

    language: _Text
    stub: _Text
    tests: _Text
    reference: _Text
    time_limit_seconds: Annotated[int, Field(ge=1)] = 10
    complexity: ComplexityModel | None = None

    def to_domain(self) -> KataSpec:
        return KataSpec(
            language=self.language,
            stub=self.stub,
            tests=self.tests,
            reference=self.reference,
            time_limit_seconds=self.time_limit_seconds,
            complexity=self.complexity.to_domain() if self.complexity else None,
        )


class GitScenarioSpecModel(_SpecModel):
    """The `scenario:` block."""

    fixture: _Text
    reference: _Text
    checks: tuple[CheckModel, ...]
    allowed_commands: frozenset[_Text]
    counter_examples: tuple[CounterExampleModel, ...] = ()
    max_commands: Annotated[int, Field(ge=1)] = 25
    command_timeout_seconds: Annotated[int, Field(ge=1)] = 10
    #: No upper bound here: "not more than `max_commands`" is a relationship
    #: between two fields, which `GitScenarioSpec` already enforces and this
    #: module does not restate (see the module docstring).
    reference_failing_commands: Annotated[int, Field(ge=0)] = 0

    @field_validator("allowed_commands")
    @classmethod
    def _must_be_bare_program_names(cls, value: frozenset[str]) -> frozenset[str]:
        """`allowed_commands` is matched against `argv[0]`, never a whole line.

        An entry like `git revert` can therefore never match anything, and an
        author who writes one has an exercise that is quietly stricter than they
        think it is.
        """
        offenders = sorted(name for name in value if name.split() != [name])
        if offenders:
            raise ValueError(
                f"allowed_commands holds program names, not command lines: "
                f"{', '.join(repr(name) for name in offenders)}"
            )
        return value

    def to_domain(self) -> GitScenarioSpec:
        return GitScenarioSpec(
            fixture=self.fixture,
            reference=self.reference,
            checks=tuple(check.domain for check in self.checks),
            allowed_commands=self.allowed_commands,
            counter_examples=tuple(
                example.to_domain() for example in self.counter_examples
            ),
            max_commands=self.max_commands,
            command_timeout_seconds=self.command_timeout_seconds,
            reference_failing_commands=self.reference_failing_commands,
        )


class SqlDrillSpecModel(_SpecModel):
    """The `drill:` block.

    No `allowed_commands` and no `max_commands`, because a drill has no command
    console — `SqlDrillSpec` says why that cost nothing. What it does have that
    a kata does not is `checks:`, over the drill vocabulary.
    """

    seed: _Text
    stub: _Text
    reference: _Text
    checks: tuple[DrillCheckModel, ...]
    counter_examples: tuple[CounterExampleModel, ...] = ()
    statement_timeout_seconds: Annotated[int, Field(ge=1)] = 10

    def to_domain(self) -> SqlDrillSpec:
        return SqlDrillSpec(
            seed=self.seed,
            stub=self.stub,
            reference=self.reference,
            checks=tuple(check.domain for check in self.checks),
            counter_examples=tuple(
                example.to_domain() for example in self.counter_examples
            ),
            statement_timeout_seconds=self.statement_timeout_seconds,
        )


# --- the file itself -------------------------------------------------------


class _ExerciseFileBase(_Model):
    """Metadata common to every kind.

    The kind-specific spec is built and cached by the spec model itself, so
    everything here is metadata plus the two properties that let one loader
    handle both kinds.
    """

    schema_version: Literal[1]
    kind: ExerciseKind
    id: _Text
    title: _Text
    prompt: _Text
    difficulty: Difficulty
    estimated_minutes: Annotated[int, Field(ge=1)]
    tags: tuple[_Text, ...] = ()
    hints: tuple[_Text, ...] = ()

    @field_validator("id")
    @classmethod
    def _must_be_an_exercise_id(cls, value: str) -> str:
        ExerciseId(value)
        return value

    @field_validator("tags")
    @classmethod
    def _must_be_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for name in value:
            tag(name)
        duplicates = sorted({name for name in value if value.count(name) > 1})
        if duplicates:
            raise ValueError(f"repeated tag(s): {', '.join(duplicates)}")
        return value

    @property
    def spec_model(self) -> _SpecModel:
        raise NotImplementedError

    @property
    def spec(self) -> ExerciseSpec:
        """The validated domain spec, built during validation."""
        return self.spec_model.domain

    def to_exercise(self, *, notes: str) -> Exercise:
        """Assemble the domain aggregate.

        `notes` comes from `notes.md` rather than from the YAML, so the loader
        supplies it — which is why this takes an argument and is not a property.
        """
        return Exercise(
            id=ExerciseId(self.id),
            kind=self.kind,
            title=self.title,
            prompt=self.prompt,
            difficulty=self.difficulty,
            tags=tuple(tag(name) for name in self.tags),
            estimated_minutes=self.estimated_minutes,
            hints=tuple(Hint(text) for text in self.hints),
            notes=notes,
            spec=self.spec,
        )


class KataFile(_ExerciseFileBase):
    """`kind: kata`, per PLAN.md §5.1."""

    # Narrows the base's `kind` to one value, which is what makes it usable as
    # the union's discriminator without a second field to keep in step with it.
    kind: Literal[ExerciseKind.KATA]
    kata: KataSpecModel

    @property
    def spec_model(self) -> KataSpecModel:
        return self.kata


class GitScenarioFile(_ExerciseFileBase):
    """`kind: git_scenario`, per PLAN.md §5.2."""

    kind: Literal[ExerciseKind.GIT_SCENARIO]
    scenario: GitScenarioSpecModel

    @property
    def spec_model(self) -> GitScenarioSpecModel:
        return self.scenario


class SqlDrillFile(_ExerciseFileBase):
    """`kind: sql_drill`, per PLAN.md §5.5."""

    kind: Literal[ExerciseKind.SQL_DRILL]
    drill: SqlDrillSpecModel

    @property
    def spec_model(self) -> SqlDrillSpecModel:
        return self.drill


type ExerciseFile = KataFile | GitScenarioFile | SqlDrillFile

#: The single entry point for parsing. A `TypeAdapter` over the tagged union
#: rather than a wrapper model, so what an author sees is the discriminator's
#: own error rather than one nested a level deeper than the file it describes.
EXERCISE_FILE: TypeAdapter[ExerciseFile] = TypeAdapter(
    Annotated[KataFile | GitScenarioFile | SqlDrillFile, Field(discriminator="kind")]
)
