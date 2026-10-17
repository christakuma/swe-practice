"""Every container exercise on disk, solved and failed, through the real parser.

The drill suite's standard (`test_drills.py`), applied to the fourth kind: the
reference passes with no advisories, the stub fails, and **every
counter-example fails exactly the checks it declares** — no fewer, which would
make it prove nothing, and no more, which would make it evidence about some
other mistake.

**What this file cannot see is whether the tickets are true.** It proves the
grader agrees with the author; it cannot prove that the stub's container really
resets connections or really waits ten seconds to stop. That is
`tests/docker/`, which runs against a real daemon and is opt-in (ADR 0030).

Graded through `grade_query` over a `ParsedBuildQuery`, which is the function
`ContainerGrader.grade` calls once it has read the workspace. Fast for the
drill suite's reason: nothing here starts a process.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.container import (
    DEFINITION_CHECK_ID,
    ParsedBuildQuery,
    context_files,
    grade_query,
)
from practice.adapters.content import ContentError, load_exercise
from practice.adapters.content.validation import discover
from practice.config import content_root
from practice.domain.containers import registry as containers
from practice.domain.exercise import ContainerSpec
from practice.domain.verdict import Outcome

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.verdict import Verdict

CONTENT_ROOT = content_root()


def _container_directories() -> list[Path]:
    found = []
    for directory in sorted(discover(CONTENT_ROOT)):
        try:
            exercise = load_exercise(directory)
        except ContentError:
            continue
        if isinstance(exercise.spec, ContainerSpec):
            found.append(directory)
    return found


EXERCISES = _container_directories()
IDS = [directory.relative_to(CONTENT_ROOT).as_posix() for directory in EXERCISES]

_VERDICTS: dict[tuple[Path, str], Verdict] = {}


def spec_of(directory: Path) -> ContainerSpec:
    spec = load_exercise(directory).spec
    assert isinstance(spec, ContainerSpec)
    return spec


def grade(directory: Path, filename: str) -> Verdict:
    """Grade one answer file as the editable file of its exercise."""
    key = (directory, filename)
    if key not in _VERDICTS:
        spec = spec_of(directory)
        query = ParsedBuildQuery(
            context=context_files(directory / spec.context),
            editable=spec.stub,
            source=(directory / filename).read_text(encoding="utf-8"),
        )
        _VERDICTS[key] = grade_query(spec, query)
    return _VERDICTS[key]


def _describe(verdict: Verdict) -> str:
    lines = [
        f"  {report.check_id}: expected {report.expected!r}, got {report.actual!r}"
        for report in verdict.reports
        if not report.passed
    ]
    return "\n".join(["", *lines]) if lines else " (nothing failed)"


# --- the references --------------------------------------------------------


@pytest.mark.parametrize("directory", EXERCISES, ids=IDS)
def test_the_reference_passes_with_no_advisories(directory: Path) -> None:
    """A reference is the best answer, not merely an accepted one."""
    verdict = grade(directory, spec_of(directory).reference)
    assert verdict.outcome is Outcome.PASS, _describe(verdict)


@pytest.mark.parametrize("directory", EXERCISES, ids=IDS)
def test_the_stub_does_not_pass(directory: Path) -> None:
    verdict = grade(directory, spec_of(directory).stub)
    assert not verdict.passed, _describe(verdict)


# --- the counter-examples --------------------------------------------------


@pytest.mark.parametrize("directory", EXERCISES, ids=IDS)
def test_every_counter_example_fails_exactly_what_it_declares(
    directory: Path,
) -> None:
    for example in spec_of(directory).counter_examples:
        verdict = grade(directory, example.file)
        failed = {r.check_id for r in verdict.reports if not r.passed}
        assert failed == set(example.expect_failures), (
            f"{example.file} declares it fails {sorted(example.expect_failures)} "
            f"and actually fails {sorted(failed)}{_describe(verdict)}"
        )


@pytest.mark.parametrize("directory", EXERCISES, ids=IDS)
def test_every_counter_example_parses(directory: Path) -> None:
    """A wrong answer Docker would *accept*, not a broken file.

    A counter-example with a typo in it fails `definition-parsed` and would
    then be excluded from the exact-set test above only by luck. It would be
    evidence about the typo, not the mistake it was written for.
    """
    for example in spec_of(directory).counter_examples:
        verdict = grade(directory, example.file)
        [parsed] = [r for r in verdict.reports if r.check_id == DEFINITION_CHECK_ID]
        assert parsed.passed, f"{example.file} did not parse: {parsed.actual}"


@pytest.mark.parametrize("directory", EXERCISES, ids=IDS)
def test_every_exercise_has_a_counter_example(directory: Path) -> None:
    assert spec_of(directory).counter_examples


# --- the library as a whole ------------------------------------------------


def test_there_are_six_container_exercises() -> None:
    """A literal count, so a seventh is a deliberate edit rather than a surprise."""
    assert len(EXERCISES) == 6


def test_every_container_assertion_is_used_by_some_exercise() -> None:
    """§13's rule, held over the eight: an assertion nothing names should go."""
    used = {
        check.assertion
        for directory in EXERCISES
        for check in spec_of(directory).checks
    }
    assert used == containers.CONTAINER_ASSERTIONS, (
        f"unused: {sorted(containers.CONTAINER_ASSERTIONS - used)}"
    )


@pytest.mark.parametrize("directory", EXERCISES, ids=IDS)
def test_the_context_does_not_hold_the_editable_file(directory: Path) -> None:
    """The stub is copied in beside the context; a second copy would shadow it."""
    spec = spec_of(directory)
    assert not (directory / spec.context / spec.stub).exists()
