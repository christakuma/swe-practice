"""The content aggregate and the spec union, including the invariants that stop
an exercise from being vacuously passable.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, ClassVar

import pytest

from practice.domain.errors import InvalidValueError
from practice.domain.exercise import (
    CheckSpec,
    ComplexityExpectation,
    CounterExample,
    Difficulty,
    EditableSource,
    Exercise,
    ExerciseFilter,
    ExerciseKind,
    GitScenarioSpec,
    Hint,
    KataSpec,
    SqlDrillSpec,
    editable_source,
)
from practice.domain.ids import ExerciseId, tag
from practice.domain.verdict import Severity

# Builders over `dataclasses.replace` rather than **kwargs dicts: the override
# keywords stay type-checked, and because `replace` re-runs `__post_init__` the
# invalid cases below exercise the real construction path.
_CHECK = CheckSpec(
    id="content-restored",
    label="The committed tree matches the state before the bad commit",
    severity=Severity.REQUIRED,
    assertion="tree_equals",
)

_KATA = KataSpec(
    language="python",
    stub="stub.py",
    tests="tests.py",
    reference="solution.py",
)

_SCENARIO = GitScenarioSpec(
    fixture="fixture.sh",
    reference="solution.cmds",
    checks=(_CHECK,),
    allowed_commands=frozenset({"git", "cat"}),
)

_DRILL = SqlDrillSpec(
    seed="seed.sql",
    stub="stub.sql",
    reference="solution.sql",
    checks=(_CHECK,),
)

_EXERCISE = Exercise(
    id=ExerciseId("git/revert-a-pushed-commit"),
    kind=ExerciseKind.GIT_SCENARIO,
    title="Undo a commit that is already on origin",
    prompt="You pushed the most recent commit to origin/main.",
    difficulty=Difficulty.MEDIUM,
    tags=(tag("history"), tag("revert")),
    estimated_minutes=10,
    hints=(Hint("Read build.sh, then parser.py."),),
    notes="Why revert and not reset.",
    spec=_SCENARIO,
)


def a_check(**overrides: Any) -> CheckSpec:
    return replace(_CHECK, **overrides)


def a_drill(**overrides: Any) -> SqlDrillSpec:
    return replace(_DRILL, **overrides)


def a_kata(**overrides: Any) -> KataSpec:
    return replace(_KATA, **overrides)


def a_scenario(**overrides: Any) -> GitScenarioSpec:
    return replace(_SCENARIO, **overrides)


def an_exercise(**overrides: Any) -> Exercise:
    return replace(_EXERCISE, **overrides)


class TestHintAndComplexity:
    @pytest.mark.parametrize("text", ["", "   ", "\n"])
    def test_a_hint_cannot_be_blank(self, text: str) -> None:
        with pytest.raises(InvalidValueError):
            Hint(text)

    def test_a_complexity_expectation_holds_both_axes(self) -> None:
        expectation = ComplexityExpectation(expected_time="O(n)", expected_space="O(n)")

        assert expectation.expected_time == "O(n)"

    def test_a_complexity_expectation_needs_both_axes(self) -> None:
        with pytest.raises(InvalidValueError):
            ComplexityExpectation(expected_time="O(n)", expected_space=" ")


class TestCheckSpec:
    def test_params_default_to_empty_and_negation_defaults_to_off(self) -> None:
        check = a_check()

        assert dict(check.params) == {}
        assert check.negated is False
        assert check.is_required is True

    def test_params_are_copied_so_the_caller_cannot_mutate_them_later(self) -> None:
        params: dict[str, str] = {"ref": "HEAD"}
        check = a_check(params=params)

        params["ref"] = "main"

        assert check.params["ref"] == "HEAD"

    def test_params_view_is_read_only(self) -> None:
        check = a_check(params={"ref": "HEAD"})

        with pytest.raises(TypeError):
            check.params["ref"] = "main"  # type: ignore[index]

    @pytest.mark.parametrize("check_id", ["", "Content-Restored", "content_restored"])
    def test_rejects_a_check_id_that_is_not_kebab_case(self, check_id: str) -> None:
        with pytest.raises(InvalidValueError):
            a_check(id=check_id)

    def test_rejects_a_blank_label(self) -> None:
        with pytest.raises(InvalidValueError, match="no label"):
            a_check(label="  ")

    @pytest.mark.parametrize("assertion", ["", "tree-equals", "TreeEquals", "1_equals"])
    def test_rejects_an_assertion_name_that_cannot_be_a_registry_key(
        self, assertion: str
    ) -> None:
        with pytest.raises(InvalidValueError, match="registry key"):
            a_check(assertion=assertion)

    def test_advisory_checks_are_not_required(self) -> None:
        assert a_check(severity=Severity.ADVISORY).is_required is False


class TestGitScenarioSpec:
    def test_exposes_its_checks_by_id(self) -> None:
        spec = a_scenario(
            checks=(a_check(id="content-restored"), a_check(id="clean-worktree"))
        )

        assert spec.check_ids == {"content-restored", "clean-worktree"}
        assert spec.check("clean-worktree").id == "clean-worktree"
        assert spec.kind is ExerciseKind.GIT_SCENARIO

    def test_looking_up_an_unknown_check_is_an_error_not_a_none(self) -> None:
        with pytest.raises(InvalidValueError, match="no such check"):
            a_scenario().check("nope")

    def test_requires_at_least_one_check(self) -> None:
        with pytest.raises(InvalidValueError, match="at least one check"):
            a_scenario(checks=())

    def test_rejects_a_scenario_whose_checks_are_all_advisory(self) -> None:
        """An all-advisory scenario passes vacuously, which is worse than no
        exercise at all (PLAN.md §5.4).
        """
        with pytest.raises(InvalidValueError, match="vacuously"):
            a_scenario(checks=(a_check(severity=Severity.ADVISORY),))

    def test_rejects_duplicate_check_ids(self) -> None:
        with pytest.raises(InvalidValueError, match="duplicate check ids: clean"):
            a_scenario(checks=(a_check(id="clean"), a_check(id="clean")))

    def test_required_checks_are_separable_from_advisories(self) -> None:
        spec = a_scenario(
            checks=(
                a_check(id="content-restored"),
                a_check(id="no-force-push", severity=Severity.ADVISORY),
            )
        )

        assert [check.id for check in spec.required_checks] == ["content-restored"]

    def test_rejects_a_counter_example_naming_a_check_that_does_not_exist(self) -> None:
        """A counter-example can never fail a check that is not in the list, so
        this would ship a content file CI could never satisfy.
        """
        with pytest.raises(InvalidValueError, match="unknown check"):
            a_scenario(
                counter_examples=(
                    CounterExample(
                        file="naive-reset-force.cmds",
                        expect_failures=frozenset({"history-preserved"}),
                    ),
                )
            )

    def test_accepts_a_counter_example_naming_a_real_check(self) -> None:
        spec = a_scenario(
            checks=(a_check(id="history-preserved"),),
            counter_examples=(
                CounterExample(
                    file="naive-reset-force.cmds",
                    expect_failures=frozenset({"history-preserved"}),
                ),
            ),
        )

        assert spec.counter_examples[0].file == "naive-reset-force.cmds"

    def test_a_counter_example_must_declare_what_it_fails(self) -> None:
        with pytest.raises(InvalidValueError, match="at least one check"):
            CounterExample(file="naive.cmds", expect_failures=frozenset())

    def test_a_counter_example_needs_a_file(self) -> None:
        with pytest.raises(InvalidValueError, match="needs a file"):
            CounterExample(file="  ", expect_failures=frozenset({"clean"}))

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("fixture", " "),
            ("reference", " "),
            ("allowed_commands", frozenset()),
            ("max_commands", 0),
            ("command_timeout_seconds", 0),
        ],
    )
    def test_rejects_unusable_limits(self, field_name: str, value: object) -> None:
        with pytest.raises(InvalidValueError):
            a_scenario(**{field_name: value})

    def test_defaults_to_a_reference_solution_that_never_fails(self) -> None:
        assert a_scenario().reference_failing_commands == 0

    @pytest.mark.parametrize("count", [-1, 26])
    def test_rejects_a_failing_command_count_outside_the_budget(
        self, count: int
    ) -> None:
        """Negative is nonsense; above `max_commands` is an exercise whose
        reference cannot exist, since it would have to run more commands than the
        exercise permits in order to fail that many of them.
        """
        with pytest.raises(InvalidValueError, match="reference_failing_commands"):
            a_scenario(max_commands=25, reference_failing_commands=count)


class TestKataSpec:
    def test_defaults_a_time_limit_and_no_declared_complexity(self) -> None:
        spec = a_kata()

        assert spec.time_limit_seconds == 10
        assert spec.complexity is None
        assert spec.kind is ExerciseKind.KATA

    @pytest.mark.parametrize("field_name", ["language", "stub", "tests", "reference"])
    def test_every_file_reference_is_required(self, field_name: str) -> None:
        with pytest.raises(InvalidValueError, match=field_name):
            a_kata(**{field_name: "  "})

    def test_rejects_a_zero_time_limit(self) -> None:
        with pytest.raises(InvalidValueError):
            a_kata(time_limit_seconds=0)


class TestSpecFilenamesAreNamesAndNotPaths:
    """Every filename a spec names is resolved against two different roots, and
    a path escapes both.

    The provisioner copies `content_root / exercise_id / name` to
    `<workspace>/repo/name`, so `stub: ../../../x` reads outside the library and
    writes outside the workspace — and `validate_library` could not catch it,
    because `(directory / name).is_file()` is satisfied by a traversal pointing
    at something real. Held in the domain rather than in the schema so both
    `ContentRepository` implementations inherit it: a pack's `exercise.yaml` is
    content somebody else wrote, and `install_pack` guards archive members
    against the same thing for the same reason.
    """

    #: Three spellings of a path and two of a name that is not one. The
    #: backslash matters on its own: a POSIX `PurePath` reads it as one
    #: component, so a check that only split on `/` would pass it through to a
    #: Windows `joinpath`, where it is a separator.
    ESCAPES: ClassVar = [
        "../../../secret.txt",
        "..\\..\\secret.txt",
        "/etc/passwd",
        "sub/stub.py",
        "C:stub.py",
        "..",
    ]

    @pytest.mark.parametrize("value", ESCAPES)
    @pytest.mark.parametrize("field_name", ["stub", "tests", "reference"])
    def test_a_kata_refuses_one(self, field_name: str, value: str) -> None:
        with pytest.raises(InvalidValueError, match="cannot be a path"):
            a_kata(**{field_name: value})

    @pytest.mark.parametrize("value", ESCAPES)
    @pytest.mark.parametrize("field_name", ["fixture", "reference"])
    def test_a_scenario_refuses_one(self, field_name: str, value: str) -> None:
        with pytest.raises(InvalidValueError, match="cannot be a path"):
            a_scenario(**{field_name: value})

    @pytest.mark.parametrize("value", ESCAPES)
    @pytest.mark.parametrize("field_name", ["seed", "stub", "reference"])
    def test_a_drill_refuses_one(self, field_name: str, value: str) -> None:
        with pytest.raises(InvalidValueError, match="cannot be a path"):
            a_drill(**{field_name: value})

    @pytest.mark.parametrize("value", ESCAPES)
    def test_a_counter_example_refuses_one(self, value: str) -> None:
        """Counter-examples are in `referenced_files` too, and are read by the
        content suite rather than the provisioner — which is a second reader of
        the same path, not a reason to trust it.
        """
        with pytest.raises(InvalidValueError, match="cannot be a path"):
            CounterExample(file=value, expect_failures=frozenset({"content-restored"}))

    def test_an_ordinary_filename_is_still_accepted(self) -> None:
        """The rule refuses a capability nothing in the library uses: every
        filename it ships is already a bare name.
        """
        assert a_kata(stub="stub.py").stub == "stub.py"
        assert a_drill(seed="seed.sql").seed == "seed.sql"


class TestExercise:
    def test_carries_its_spec_and_hint_count(self) -> None:
        exercise = an_exercise()

        assert isinstance(exercise.spec, GitScenarioSpec)
        assert exercise.hint_count == 1

    def test_kind_must_agree_with_the_spec_it_carries(self) -> None:
        with pytest.raises(InvalidValueError, match="carries a"):
            an_exercise(kind=ExerciseKind.KATA)

    def test_a_kata_exercise_is_accepted_with_a_kata_spec(self) -> None:
        exercise = an_exercise(
            id=ExerciseId("katas/two-sum"),
            kind=ExerciseKind.KATA,
            spec=a_kata(),
        )

        assert exercise.kind is ExerciseKind.KATA

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [("title", " "), ("prompt", "\n"), ("estimated_minutes", 0)],
    )
    def test_rejects_missing_metadata(self, field_name: str, value: object) -> None:
        with pytest.raises(InvalidValueError):
            an_exercise(**{field_name: value})

    def test_rejects_a_repeated_tag(self) -> None:
        with pytest.raises(InvalidValueError, match="repeats a tag"):
            an_exercise(tags=(tag("history"), tag("history")))

    def test_hints_and_notes_may_be_empty_because_that_is_the_content_suites_job(
        self,
    ) -> None:
        exercise = an_exercise(hints=(), notes="")

        assert exercise.hint_count == 0


class TestExerciseFilter:
    def test_an_empty_filter_matches_everything(self) -> None:
        assert ExerciseFilter().matches(an_exercise()) is True

    def test_filters_on_kind(self) -> None:
        criteria = ExerciseFilter(kinds=frozenset({ExerciseKind.KATA}))

        assert criteria.matches(an_exercise()) is False

    def test_filters_on_difficulty(self) -> None:
        criteria = ExerciseFilter(difficulties=frozenset({Difficulty.HARD}))

        assert criteria.matches(an_exercise()) is False

    def test_tags_match_on_any_not_all(self) -> None:
        criteria = ExerciseFilter(tags=frozenset({tag("revert"), tag("rebase")}))

        assert criteria.matches(an_exercise()) is True

    def test_a_disjoint_tag_set_does_not_match(self) -> None:
        criteria = ExerciseFilter(tags=frozenset({tag("rebase")}))

        assert criteria.matches(an_exercise()) is False

    def test_all_dimensions_must_hold_together(self) -> None:
        criteria = ExerciseFilter(
            kinds=frozenset({ExerciseKind.GIT_SCENARIO}),
            difficulties=frozenset({Difficulty.MEDIUM}),
            tags=frozenset({tag("history")}),
        )

        assert criteria.matches(an_exercise()) is True


class TestSqlDrillSpec:
    """The third kind's spec, and the invariants it shares with a scenario.

    The shared ones are tested here as well as under `TestGitScenarioSpec`
    rather than only against `validate_checks` directly. They are the rules that
    stop an exercise being vacuously passable, and the claim worth holding is
    that *a drill* cannot be built vacuously -- which is a claim about this
    constructor, not about a helper it happens to call today.
    """

    def test_knows_its_own_kind(self) -> None:
        assert a_drill().kind is ExerciseKind.SQL_DRILL

    @pytest.mark.parametrize("field", ["seed", "stub", "reference"])
    def test_requires_each_of_its_three_files(self, field: str) -> None:
        with pytest.raises(InvalidValueError, match=f"needs a {field}"):
            a_drill(**{field: "   "})

    def test_requires_at_least_one_check(self) -> None:
        with pytest.raises(InvalidValueError, match="a drill needs at least one check"):
            a_drill(checks=())

    def test_rejects_a_drill_whose_checks_are_all_advisory(self) -> None:
        """The vacuous-pass guard, in a drill's own vocabulary.

        A drill graded only by advisories reports `PASS_WITH_ADVISORIES` for an
        empty file, which is worse than not shipping the exercise.
        """
        with pytest.raises(InvalidValueError, match="a drill needs at least one"):
            a_drill(checks=(a_check(severity=Severity.ADVISORY),))

    def test_rejects_duplicate_check_ids(self) -> None:
        with pytest.raises(InvalidValueError, match="duplicate check ids: rows-match"):
            a_drill(
                checks=(
                    a_check(id="rows-match"),
                    a_check(id="rows-match", assertion="result_row_count"),
                )
            )

    def test_rejects_a_counter_example_naming_a_check_that_does_not_exist(self) -> None:
        with pytest.raises(InvalidValueError, match="expects unknown check"):
            a_drill(
                counter_examples=(
                    CounterExample(
                        file="forgot-the-join.sql",
                        expect_failures=frozenset({"no-such-check"}),
                    ),
                )
            )

    def test_accepts_a_counter_example_naming_a_real_check(self) -> None:
        spec = a_drill(
            counter_examples=(
                CounterExample(
                    file="forgot-the-join.sql",
                    expect_failures=frozenset({"content-restored"}),
                ),
            )
        )

        assert spec.counter_example_files == ("forgot-the-join.sql",)

    def test_rejects_a_timeout_below_a_second(self) -> None:
        with pytest.raises(InvalidValueError, match="statement_timeout_seconds"):
            a_drill(statement_timeout_seconds=0)

    def test_required_checks_are_separable_from_advisories(self) -> None:
        spec = a_drill(
            checks=(
                a_check(id="rows-match"),
                a_check(id="used-an-index", severity=Severity.ADVISORY),
            )
        )

        assert [check.id for check in spec.required_checks] == ["rows-match"]
        assert spec.check_ids == frozenset({"rows-match", "used-an-index"})

    def test_looking_up_an_unknown_check_is_an_error_not_a_none(self) -> None:
        with pytest.raises(InvalidValueError, match="no such check"):
            a_drill().check("nope")

    def test_lists_every_sibling_file_it_names(self) -> None:
        """What validation checks the existence of and what the provisioner copies.

        All four roles, which is what makes a drill different from a kata: the
        counter-examples are SQL files like the reference, so they are named by
        the same list rather than by a second one.
        """
        spec = a_drill(
            counter_examples=(
                CounterExample(
                    file="forgot-the-join.sql",
                    expect_failures=frozenset({"content-restored"}),
                ),
            )
        )

        assert spec.referenced_files == (
            "seed.sql",
            "stub.sql",
            "solution.sql",
            "forgot-the-join.sql",
        )


class TestEditableSource:
    """The question five call sites were asking by way of `isinstance(.., KataSpec)`.

    Held as a property of the union rather than of any one kind, because the
    whole reason it exists is that the answer is no longer derivable from "is
    this a kata".
    """

    def test_a_kata_is_edited_in_its_stub(self) -> None:
        assert editable_source(a_kata()) == EditableSource(
            filename="stub.py", language="python", reference="solution.py"
        )

    def test_a_drill_is_edited_in_its_stub_too(self) -> None:
        assert editable_source(a_drill()) == EditableSource(
            filename="stub.sql", language="sql", reference="solution.sql"
        )

    def test_a_scenario_has_no_editable_file_at_all(self) -> None:
        """`None` is an answer and not a gap -- a scenario's surface is a console."""
        assert editable_source(a_scenario()) is None

    def test_the_language_comes_from_the_spec_not_the_extension(self) -> None:
        """So a second kata language is a content change, per §15 Q3."""
        assert editable_source(a_kata(language="javascript", stub="stub.js")) == (
            EditableSource(
                filename="stub.js", language="javascript", reference="solution.py"
            )
        )

    def test_it_carries_the_authors_own_answer_as_well(self) -> None:
        """Which is why `--reference` needs no second `isinstance`: the
        reference grades through the same path a solver's file takes.
        """
        source = editable_source(a_drill(reference="model-answer.sql"))

        assert source is not None
        assert source.reference == "model-answer.sql"
