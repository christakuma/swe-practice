"""Every git scenario, graded. The oracle PLAN.md §9 asks for and Phase 2 deferred.

The suite that keeps a growing library honest, and the one that makes the earlier
content tests mean something. `validate` proves a scenario is *structurally* valid.
`test_fixtures.py` proves its fixture runs and its command lists replay. Neither
knows whether the end state is **right**, and this does:

* `solution.cmds`, replayed through the real command policy, must pass every
  `required` check;
* each counter-example must fail **exactly** the checks its `expect_failures`
  declares — not "at least one".

**"Exactly" is the whole point of the file.** "Fails at least one check" would let a
counter-example rot into failing for an unrelated reason with CI none the wiser: a
naive list that refers to `HEAD@{3}` depends on a reflog position that shifts when a
command is added anywhere above it, so an innocuous edit could leave it failing
`branch-restored` instead of `on-a-branch` — still red, still green in CI, and no
longer teaching the thing it was written to teach (§5.4).

Both halves run through the **real use cases**, not through a grader called directly.
That is §5.3's fidelity guarantee carried all the way: if the rules a reference
solution is validated against are not byte-for-byte the rules a solver's input is
executed against, then CI proves a solution exists rather than a solution exists
*within the rules*, and a scenario can ship unsolvable with a green build.

Parametrized over the real `content/` directory, so adding an exercise adds test
cases without touching this file. Each command list is graded **once** and shared by
the tests that read it: a grading pass provisions a workspace and runs a fixture, so
re-grading per assertion would make the suite cost more than it is worth and get
skipped, which is worse than a coarser one that runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.composition import build_services
from practice.config import content_root
from practice.domain.commands import parse_command_list
from practice.domain.exercise import GitScenarioSpec
from practice.domain.ids import ExerciseId
from tests.content.conftest import identify, scenario_directories

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from practice.application.dto import Submission
    from practice.composition import Services
    from practice.domain.exercise import Exercise
    from practice.domain.verdict import CheckReport

SCENARIO_DIRECTORIES = scenario_directories()


@pytest.fixture(params=SCENARIO_DIRECTORIES, ids=identify)
def scenario_directory(request: pytest.FixtureRequest) -> Path:
    directory: Path = request.param
    return directory


@pytest.fixture
def services(tmp_path: Path) -> Services:
    """The real object graph, pointed at a disposable workspace root.

    The real one, deliberately: this suite's job is to prove the shipped content is
    gradable through the shipped wiring, and a hand-assembled graph would prove it
    about a graph nobody runs. Only the workspace root is redirected, so a CI run
    cannot collide with a session the developer has open.
    """
    return build_services(content=content_root(), workspaces=tmp_path / "ws")


@pytest.fixture
def exercise(services: Services, scenario_directory: Path) -> Exercise:
    """The exercise through the content repository, not the loader.

    Because that is how the use cases get it: an exercise this suite loaded directly
    could differ from the one a solver is graded against, which is precisely the
    drift the suite exists to catch.
    """
    found = services.content.get(ExerciseId(identify(scenario_directory)))
    assert found is not None, f"{identify(scenario_directory)} is not in the library"
    return found


@pytest.fixture
def spec(exercise: Exercise) -> GitScenarioSpec:
    assert isinstance(exercise.spec, GitScenarioSpec)
    return exercise.spec


@pytest.fixture
def reference(
    services: Services,
    exercise: Exercise,
    spec: GitScenarioSpec,
    scenario_directory: Path,
) -> Submission:
    """`solution.cmds`, graded once for every test that reads the result."""
    return grade(services, exercise, scenario_directory / spec.reference)


@pytest.fixture
def counter_examples(
    services: Services,
    exercise: Exercise,
    spec: GitScenarioSpec,
    scenario_directory: Path,
) -> Mapping[str, Submission]:
    """Every counter-example, each graded in its own workspace.

    Its own, so the order they are declared in cannot matter: replaying the second on
    top of the first would make what it proves depend on where the first left off.
    """
    return {
        example.file: grade(services, exercise, scenario_directory / example.file)
        for example in spec.counter_examples
    }


def grade(services: Services, exercise: Exercise, commands: Path) -> Submission:
    """Start an attempt, replay a command list, submit, and hand back the verdict.

    Through `RunScenarioCommand`, which means through the real policy, the real
    allowlist and the real budget. A command the exercise does not permit raises here
    rather than being quietly executed, which is §5.3's guarantee in one line.

    A non-zero exit is not an error. Some counter-examples are *meant* to hit one —
    that is sometimes the lesson — and what matters is that every line was legal and
    the list ran to the end.
    """
    started = services.start_attempt(exercise.id)
    run = services.run_scenario_command
    for command in parse_command_list(commands.read_text(encoding="utf-8")):
        run(started.attempt.id, command.text)
    return services.submit_scenario(started.attempt.id)


def describe(reports: Iterable[CheckReport]) -> str:
    """Failing checks, as lines a content author can act on."""
    return "\n".join(
        f"      {report.check_id}: expected {report.expected}, got {report.actual}"
        for report in reports
    )


# --- the walk --------------------------------------------------------------


def test_there_are_scenarios_to_grade() -> None:
    """Without this, every parametrized test below is vacuously true."""
    assert SCENARIO_DIRECTORIES


# --- the reference solution ------------------------------------------------


def test_its_reference_solution_passes_every_required_check(
    reference: Submission, spec: GitScenarioSpec
) -> None:
    """The oracle. A scenario whose own reference answer fails a required check is
    either an unsolvable exercise or a wrong check, and both ship silently without
    this.
    """
    assert reference.verdict.failures == (), (
        f"{spec.reference} fails {len(reference.verdict.failures)} required "
        f"check(s):\n{describe(reference.verdict.failures)}"
    )


def test_its_reference_solution_trips_no_advisory(
    reference: Submission, spec: GitScenarioSpec
) -> None:
    """A separate test, and a softer claim than the one above.

    Every exercise in the library passes its own advisories today, and that is worth
    knowing: an advisory nobody's reference answer satisfies is usually an advisory
    whose pattern is wrong rather than a reference that is sloppy. Kept apart from the
    required-check test so a deliberate exception can be made here one day without
    weakening the oracle.
    """
    assert reference.verdict.advisories == (), (
        f"{spec.reference} trips an advisory:\n{describe(reference.verdict.advisories)}"
    )


# --- the counter-examples --------------------------------------------------


def test_each_counter_example_fails_exactly_the_checks_it_declares(
    counter_examples: Mapping[str, Submission], spec: GitScenarioSpec
) -> None:
    """The guarantee the whole file exists for (§5.4).

    Both directions are asserted, and they catch different defects. A check it
    declared and did not fail means the assertion is too loose to tell a right answer
    from this wrong one. A check it failed and did not declare means the
    counter-example is wrong in a way its author did not intend, which is how one
    quietly stops teaching what it was written for.

    This subsumes "a counter-example actually fails": `expect_failures` is non-empty
    by a domain invariant, so an equal set is a non-empty set of *required* failures.
    Worth saying rather than adding a second grading pass to assert it again.
    """
    for example in spec.counter_examples:
        submission = counter_examples[example.file]
        failed = {report.check_id for report in submission.verdict.failures}
        declared = set(example.expect_failures)

        headline = (
            f"{example.file} declares {sorted(declared)} and fails {sorted(failed)}"
        )
        lines = [headline]
        if declared - failed:
            lines.append(f"      declared but passed: {sorted(declared - failed)}")
        if failed - declared:
            lines.append(f"      failed but not declared: {sorted(failed - declared)}")
        lines.append(describe(submission.verdict.failures))

        assert failed == declared, "\n".join(lines)
        assert not submission.passed, f"{example.file} passes"


# --- what the checks themselves have to be ---------------------------------


def test_it_ships_a_counter_example_at_all(spec: GitScenarioSpec) -> None:
    """§13 lists "assertions too loose to tell right from wrong" as a high risk, with
    counter-examples as the mitigation. An exercise with none has opted out of it, and
    the schema permits that — so this is where it gets noticed.
    """
    assert spec.counter_examples, (
        "ships no counter-example, so nothing proves its checks can fail"
    )


def test_at_least_one_required_check_is_proven_to_discriminate(
    spec: GitScenarioSpec,
) -> None:
    """Some required check has to be named by some counter-example.

    Deliberately weaker than "every required check is": `clean-worktree` is the honest
    example of one that never will be. Every exercise asserts it, no counter-example
    is *about* it, and it is still worth asserting — a solver who leaves the fix
    uncommitted has not finished. Demanding a counter-example per check would mean
    writing a wrong answer whose only flaw is an uncommitted file, which teaches
    nothing.

    What would be a defect is *no* required check being covered, which means no
    counter-example discriminates anything and the whole set is decoration.
    """
    declared = {
        check_id
        for example in spec.counter_examples
        for check_id in example.expect_failures
    }
    required = {check.id for check in spec.required_checks}

    assert declared & required, (
        f"no counter-example fails a required check, so nothing proves the checks "
        f"can tell a wrong answer from a right one; required: {sorted(required)}, "
        f"declared: {sorted(declared)}"
    )
