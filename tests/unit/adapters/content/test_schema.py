"""The exercise file schema.

Pure: these tests parse dicts, never files. The value they add over "the real
exercises still load" — which `tests/content/` covers — is the failure side. A
schema is only worth having if it rejects the right things with the right
message at the right place, and none of those three is testable by feeding it
files that are already correct.

Each rejection case asserts the **location** as well as the message. A
validation error that says "must not be blank" without saying which of eleven
fields is blank has done half the job, and the half it skipped is the half the
author needs.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from practice.adapters.content.schema import EXERCISE_FILE, GitScenarioFile, KataFile
from practice.domain.exercise import Difficulty, ExerciseKind, GitScenarioSpec, KataSpec
from practice.domain.verdict import Severity

if TYPE_CHECKING:
    from collections.abc import Callable

type Mutation = Callable[[dict[str, Any]], None]


def a_scenario() -> dict[str, Any]:
    """A minimal but complete git scenario, shaped like PLAN.md §5.2."""
    return {
        "schema_version": 1,
        "id": "git/undo-a-commit",
        "kind": "git_scenario",
        "title": "Undo a commit",
        "difficulty": "medium",
        "tags": ["history", "revert"],
        "estimated_minutes": 10,
        "prompt": "Undo the last commit without rewriting published history.",
        "hints": ["What does your teammate already have?"],
        "scenario": {
            "fixture": "fixture.sh",
            "reference": "solution.cmds",
            "counter_examples": [
                {"file": "naive.cmds", "expect_failures": ["history-preserved"]}
            ],
            "allowed_commands": ["git", "cat"],
            "max_commands": 25,
            "checks": [
                {
                    "id": "history-preserved",
                    "label": "The bad commit is still reachable",
                    "severity": "required",
                    "assert": "is_ancestor",
                    "with": {"ancestor": "@c3", "descendant": "HEAD"},
                    "explanation": "Rewriting shared history strands your team.",
                },
                {
                    "id": "no-force-push",
                    "label": "You did not force-update a shared branch",
                    "severity": "advisory",
                    "assert": "command_used",
                    "not": True,
                    "with": {"pattern": "push .*--force"},
                },
            ],
        },
    }


def a_kata() -> dict[str, Any]:
    """A minimal but complete kata, shaped like PLAN.md §5.1."""
    return {
        "schema_version": 1,
        "id": "katas/two-sum",
        "kind": "kata",
        "title": "Two Sum",
        "difficulty": "easy",
        "tags": ["arrays", "hash-map"],
        "estimated_minutes": 15,
        "prompt": "Return the indices of the two numbers that sum to the target.",
        "hints": ["What would change if the array were sorted?"],
        "kata": {
            "language": "python",
            "stub": "stub.py",
            "tests": "tests.py",
            "reference": "solution.py",
            "time_limit_seconds": 10,
            "complexity": {"expected_time": "O(n)", "expected_space": "O(n)"},
        },
    }


def rejected(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """Validate, expecting failure, and return `(location, message)` per error.

    The discriminator tag that Pydantic prepends to every location is stripped:
    it identifies which arm of the union was tried, which is noise once the arm
    was chosen correctly.
    """
    with pytest.raises(ValidationError) as caught:
        EXERCISE_FILE.validate_python(payload)
    problems = []
    for error in caught.value.errors():
        location = [str(part) for part in error["loc"]]
        if location and location[0] in set(ExerciseKind):
            location.pop(0)
        problems.append((".".join(location), error["msg"]))
    return problems


def scenario_with(mutate: Mutation) -> list[tuple[str, str]]:
    payload = a_scenario()
    mutate(payload)
    return rejected(payload)


# --- the happy path --------------------------------------------------------


def test_a_git_scenario_becomes_an_exercise() -> None:
    parsed = EXERCISE_FILE.validate_python(a_scenario())
    exercise = parsed.to_exercise(notes="why revert and not reset")

    assert isinstance(parsed, GitScenarioFile)
    assert str(exercise.id) == "git/undo-a-commit"
    assert exercise.kind is ExerciseKind.GIT_SCENARIO
    assert exercise.difficulty is Difficulty.MEDIUM
    assert exercise.notes == "why revert and not reset"
    assert isinstance(exercise.spec, GitScenarioSpec)
    assert exercise.spec.allowed_commands == frozenset({"git", "cat"})


def test_a_kata_becomes_an_exercise() -> None:
    parsed = EXERCISE_FILE.validate_python(a_kata())
    exercise = parsed.to_exercise(notes="the hash-map trade")

    assert isinstance(parsed, KataFile)
    assert exercise.kind is ExerciseKind.KATA
    assert isinstance(exercise.spec, KataSpec)
    assert exercise.spec.complexity is not None
    assert exercise.spec.complexity.expected_time == "O(n)"


def test_the_yaml_keys_that_are_python_keywords_map_across() -> None:
    """`assert:` and `not:` are the only two field names that differ from their
    YAML key, and both differ for the same unavoidable reason.
    """
    parsed = EXERCISE_FILE.validate_python(a_scenario())
    spec = parsed.to_exercise(notes="n").spec

    assert isinstance(spec, GitScenarioSpec)
    advisory = spec.check("no-force-push")
    assert advisory.assertion == "command_used"
    assert advisory.negated is True
    assert advisory.severity is Severity.ADVISORY
    assert spec.check("history-preserved").negated is False


def test_optional_fields_take_the_documented_defaults() -> None:
    payload = a_scenario()
    del payload["tags"]
    del payload["hints"]
    del payload["scenario"]["max_commands"]
    del payload["scenario"]["counter_examples"]

    exercise = EXERCISE_FILE.validate_python(payload).to_exercise(notes="n")

    assert exercise.tags == ()
    assert exercise.hints == ()
    assert isinstance(exercise.spec, GitScenarioSpec)
    assert exercise.spec.max_commands == 25
    assert exercise.spec.command_timeout_seconds == 10
    assert exercise.spec.counter_examples == ()


def test_check_params_survive_as_the_narrow_value_types() -> None:
    """`ParamValue` is deliberately not `Any`, so a check function in Phase 5 can
    exhaust the cases rather than cast. A widened type here would be silent.
    """
    payload = a_scenario()
    payload["scenario"]["checks"][0]["with"] = {
        "ref": "HEAD",
        "count": 3,
        "include_untracked": True,
        "paths": ["a.py", "b.py"],
    }

    spec = EXERCISE_FILE.validate_python(payload).to_exercise(notes="n").spec

    assert isinstance(spec, GitScenarioSpec)
    assert spec.check("history-preserved").params == {
        "ref": "HEAD",
        "count": 3,
        "include_untracked": True,
        "paths": ("a.py", "b.py"),
    }


def test_the_file_reports_the_siblings_it_references() -> None:
    """The loader uses this to check the files exist before anything else does."""
    parsed = EXERCISE_FILE.validate_python(a_scenario())

    assert set(parsed.referenced_files) == {
        "fixture.sh",
        "solution.cmds",
        "naive.cmds",
    }
    assert parsed.command_lists == ("solution.cmds", "naive.cmds")


def test_a_kata_has_no_command_lists() -> None:
    """A kata has no command console, so there is nothing to police (§4.3)."""
    assert EXERCISE_FILE.validate_python(a_kata()).command_lists == ()


# --- the discriminator -----------------------------------------------------


def test_an_unknown_kind_is_rejected_by_name() -> None:
    """The discriminator error has no field location — it is about the file as a
    whole — so the message has to carry the offending value and the legal ones.

    Asserted on substance rather than verbatim because Pydantic renders the
    legal tags as enum reprs. Keeping `ExerciseKind` as the `Literal` type is
    worth a slightly noisy message for the one field that can produce it: the
    alternative is a bare `Literal["kata"]` that no longer types as the domain
    enum everything downstream expects.
    """
    payload = a_scenario()
    payload["kind"] = "sql_drill"

    [(location, message)] = rejected(payload)

    assert location == ""
    assert "'sql_drill'" in message
    assert "'kata'" in message
    assert "'git_scenario'" in message


def test_a_kind_that_does_not_match_its_block_is_rejected() -> None:
    """`kind: kata` with a `scenario:` block is caught twice over — the missing
    `kata:` block and the unexpected `scenario:` one — which is the behaviour
    tagging on `kind` buys over a single polymorphic `spec:` field.
    """
    payload = a_scenario()
    payload["kind"] = "kata"

    assert sorted(rejected(payload)) == [
        ("kata", "Field required"),
        ("scenario", "Extra inputs are not permitted"),
    ]


# --- rejections, each with its location ------------------------------------


def test_an_unknown_key_is_an_error_rather_than_a_silent_default() -> None:
    """The most expensive content bug there is: the exercise still loads, still
    grades, and does neither the way its author wrote it.
    """
    assert scenario_with(lambda p: p.update(dificulty="medium")) == [
        ("dificulty", "Extra inputs are not permitted")
    ]


def test_an_unknown_key_inside_a_check_is_an_error_too() -> None:
    assert scenario_with(
        lambda p: p["scenario"]["checks"][0].update(explaination="oops")
    ) == [("scenario.checks.0.explaination", "Extra inputs are not permitted")]


def test_a_future_schema_version_is_refused_not_guessed_at() -> None:
    assert scenario_with(lambda p: p.update(schema_version=2)) == [
        ("schema_version", "Input should be 1")
    ]


def test_an_unregistered_assertion_is_a_build_failure() -> None:
    """A typo here is a check that never runs — one fewer constraint than the
    author wrote, with nothing to say so (PLAN.md §5.4).
    """
    assert scenario_with(
        lambda p: p["scenario"]["checks"][0].update({"assert": "tree_equal"})
    ) == [
        (
            "scenario.checks.0.assert",
            "Value error, unknown assertion 'tree_equal'; did you mean tree_equals?",
        )
    ]


def test_an_unrecognisable_assertion_fails_without_a_misleading_suggestion() -> None:
    (location, message) = scenario_with(
        lambda p: p["scenario"]["checks"][0].update({"assert": "xyzzy"})
    )[0]

    assert location == "scenario.checks.0.assert"
    assert message == "Value error, unknown assertion 'xyzzy'"


@pytest.mark.parametrize(
    ("bad_id", "reason"),
    [
        ("git/Revert", "uppercase"),
        ("revert", "one segment"),
        ("git/a/b", "three segments"),
        ("git/revert_a_commit", "underscores"),
    ],
)
def test_an_id_that_is_not_a_content_path_is_rejected(bad_id: str, reason: str) -> None:
    """The id *is* the content path, so anything else breaks the loader's own
    directory convention before it breaks anything else (PLAN.md §4.1).
    """
    (location, message) = scenario_with(lambda p: p.update(id=bad_id))[0]

    assert location == "id", reason
    assert "'<track>/<slug>'" in message


@pytest.mark.parametrize("field", ["title", "prompt"])
def test_a_blank_human_string_is_rejected_where_it_is_blank(field: str) -> None:
    assert scenario_with(lambda p: p.update({field: "   \n  "})) == [
        (field, "Value error, must not be blank")
    ]


def test_a_blank_hint_is_located_at_the_hint_not_the_list() -> None:
    assert scenario_with(lambda p: p.update(hints=["fine", ""])) == [
        ("hints.1", "Value error, must not be blank")
    ]


def test_an_estimate_of_no_time_is_rejected() -> None:
    assert scenario_with(lambda p: p.update(estimated_minutes=0)) == [
        ("estimated_minutes", "Input should be greater than or equal to 1")
    ]


def test_a_malformed_tag_is_rejected() -> None:
    (location, message) = scenario_with(lambda p: p.update(tags=["Git History"]))[0]

    assert location == "tags"
    assert "lowercase kebab-case" in message


def test_a_repeated_tag_is_rejected() -> None:
    assert scenario_with(lambda p: p.update(tags=["history", "history"])) == [
        ("tags", "Value error, repeated tag(s): history")
    ]


# --- the domain invariants, surfacing through the schema -------------------


def test_a_scenario_of_only_advisories_is_rejected() -> None:
    """The vacuous-pass hole: every check advisory means every attempt passes.
    Enforced by `GitScenarioSpec`, and this asserts the schema surfaces it with
    a location rather than letting it escape as a bare exception.
    """

    def make_everything_advisory(payload: dict[str, Any]) -> None:
        for check in payload["scenario"]["checks"]:
            check["severity"] = "advisory"

    (location, message) = scenario_with(make_everything_advisory)[0]

    assert location == "scenario"
    assert "at least one required check" in message


def test_a_counter_example_naming_an_unknown_check_is_rejected() -> None:
    (location, message) = scenario_with(
        lambda p: p["scenario"]["counter_examples"][0].update(
            expect_failures=["histry-preserved"]
        )
    )[0]

    assert location == "scenario"
    assert "expects unknown check(s): histry-preserved" in message


def test_a_counter_example_must_name_a_check_it_fails() -> None:
    """ "Fails at least one check" is too weak a contract (PLAN.md §5.4)."""
    assert scenario_with(
        lambda p: p["scenario"]["counter_examples"][0].update(expect_failures=[])
    ) == [
        (
            "scenario.counter_examples.0.expect_failures",
            "Tuple should have at least 1 item after validation, not 0",
        )
    ]


def test_the_short_form_counter_example_is_not_accepted() -> None:
    """PLAN.md §5.2 shows `counter_examples: [naive.cmds]`; §5.4 supersedes it.
    Accepting the short form would mean inventing an `expect_failures` the
    author never wrote.
    """
    (location, message) = scenario_with(
        lambda p: p["scenario"].update(counter_examples=["naive.cmds"])
    )[0]

    assert location == "scenario.counter_examples.0"
    assert "valid dictionary" in message


def test_duplicate_check_ids_are_rejected() -> None:
    (location, message) = scenario_with(
        lambda p: p["scenario"]["checks"][1].update(id="history-preserved")
    )[0]

    assert location == "scenario"
    assert "duplicate check ids: history-preserved" in message


def test_a_malformed_check_id_is_located_at_the_check() -> None:
    (location, message) = scenario_with(
        lambda p: p["scenario"]["checks"][0].update(id="History Preserved")
    )[0]

    assert location == "scenario.checks.0"
    assert "lowercase kebab-case" in message


def test_a_scenario_with_no_checks_is_rejected() -> None:
    assert scenario_with(lambda p: p["scenario"].update(checks=[])) == [
        ("scenario.checks", "Tuple should have at least 1 item after validation, not 0")
    ]


def test_a_scenario_that_allows_nothing_is_rejected() -> None:
    (location, message) = scenario_with(
        lambda p: p["scenario"].update(allowed_commands=[])
    )[0]

    assert location == "scenario.allowed_commands"
    assert "at least 1 item" in message


def test_the_allowlist_holds_program_names_not_command_lines() -> None:
    """It is matched against `argv[0]`, so `git revert` can never match."""
    (location, message) = scenario_with(
        lambda p: p["scenario"].update(allowed_commands=["git revert", "cat"])
    )[0]

    assert location == "scenario.allowed_commands"
    assert "program names, not command lines: 'git revert'" in message


@pytest.mark.parametrize(
    ("field", "value"),
    [("max_commands", 0), ("command_timeout_seconds", 0)],
)
def test_a_limit_of_zero_is_rejected(field: str, value: int) -> None:
    assert scenario_with(lambda p: p["scenario"].update({field: value})) == [
        (f"scenario.{field}", "Input should be greater than or equal to 1")
    ]


def test_a_kata_time_limit_of_zero_is_rejected() -> None:
    payload = a_kata()
    payload["kata"]["time_limit_seconds"] = 0

    assert rejected(payload) == [
        ("kata.time_limit_seconds", "Input should be greater than or equal to 1")
    ]


def test_a_half_declared_complexity_is_rejected() -> None:
    """Both axes or neither: one string cannot disagree with a two-field
    expectation on only one of them (PLAN.md §4.3).
    """
    payload = a_kata()
    del payload["kata"]["complexity"]["expected_space"]

    assert rejected(payload) == [("kata.complexity.expected_space", "Field required")]


def test_every_problem_in_a_file_is_reported_at_once() -> None:
    """Fixing one typo per run to discover the next is a bad afternoon."""
    payload = a_scenario()
    payload["estimated_minutes"] = 0
    payload["title"] = ""
    payload["scenario"]["checks"][0]["assert"] = "nope_not_real"

    assert len(rejected(payload)) == 3


# --- immutability ----------------------------------------------------------


def test_a_parsed_file_cannot_be_edited_after_validation() -> None:
    """Content is read and never written, and a mutable parse result is how an
    exercise ends up differing from the file it claims to be.
    """
    parsed = EXERCISE_FILE.validate_python(a_scenario())

    with pytest.raises(ValidationError):
        parsed.title = "something else"


def test_validating_does_not_mutate_the_payload_it_was_given() -> None:
    payload = a_scenario()
    before = copy.deepcopy(payload)

    EXERCISE_FILE.validate_python(payload)

    assert payload == before
