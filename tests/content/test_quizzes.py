"""Every quiz on disk, answered right and answered wrong (Phase 25).

The quiz half of PLAN.md §9's content suite, and the same two claims the other
kinds make: **the reference sheet passes, and the stub fails** -- here, fails
*every* question, because a blank sheet that passed one would be a question
with no answer. A fix question's counter-examples are each run against its
suite and must fail exactly the tests they name (ADR 0022); a wrong fix that
fails for some other reason is a test that is not about its own point.

**The other half is about the questions rather than the answers**, and it is
what a quiz has that the other kinds do not: it can give itself away. An
author who writes the right option first, or longest, or with an id like
`correct`, has written a pattern a solver learns without meaning to, and an
`order` question listed in its answer's order is answered by its own
statement. Those rules are checked here, over the whole library where a
pattern is a fact about the library rather than one question.

And the user's own requirement, held where it can be: **every question carries
its context**. A question is read on its own, in a fieldset of its own, so it
says what it turns on rather than leaning on a ticket three screens up.
"""

from __future__ import annotations

import itertools
from collections import Counter
from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import ContentError, load_exercise
from practice.adapters.content.validation import discover
from practice.adapters.kata import PytestKataRunner
from practice.adapters.quiz import grade_sheet
from practice.adapters.sandbox import SubprocessSandboxProvisioner, find_git
from practice.config import content_root
from practice.domain.exercise import QuizSpec
from practice.domain.ids import AttemptId
from practice.domain.quiz import Answer, QuestionFormat, parse_sheet, render_sheet

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from practice.domain.exercise import Exercise
    from practice.domain.quiz import Question
    from practice.domain.verdict import Verdict

CONTENT_ROOT = content_root()

#: Words an option id must not contain, because each one is a label on the
#: answer. Ids are what a solver types in `answers.md`, and what the
#: plain-text statement prints beside every option.
GIVEAWAY_WORDS = ("right", "correct", "wrong", "best", "answer", "true", "false")

#: The most any one authored position may hold the right option, across the
#: library's single-choice questions. The page shuffles per attempt; the
#: terminal and the tutor print the authored order, and this is what keeps
#: that order from being a pattern.
MOST_IN_ONE_POSITION = 0.5

#: The most often the right option may be the strictly longest one, or the
#: strictly shortest. The tempting wrong answer should be as fully argued as
#: the right one.
MOST_OFTEN_LONGEST = 0.5


def _identify(directory: Path) -> str:
    return directory.relative_to(CONTENT_ROOT).as_posix()


def _quiz_directories() -> list[Path]:
    """Every quiz directory. One that will not load is `validate`'s to report."""
    found = []
    for directory in sorted(discover(CONTENT_ROOT)):
        try:
            exercise = load_exercise(directory)
        except ContentError:
            continue
        if isinstance(exercise.spec, QuizSpec):
            found.append(directory)
    return found


QUIZ_DIRECTORIES = _quiz_directories()


def _quizzes() -> list[tuple[Exercise, QuizSpec]]:
    pairs = []
    for directory in QUIZ_DIRECTORIES:
        exercise = load_exercise(directory)
        assert isinstance(exercise.spec, QuizSpec)
        pairs.append((exercise, exercise.spec))
    return pairs


def _questions(fmt: QuestionFormat) -> list[Question]:
    return [
        question
        for _, spec in _quizzes()
        for question in spec.questions
        if question.format is fmt
    ]


type Grade = Callable[[str], Verdict]


@pytest.fixture(params=QUIZ_DIRECTORIES, ids=_identify)
def quiz_directory(request: pytest.FixtureRequest) -> Path:
    directory: Path = request.param
    return directory


@pytest.fixture
def exercise(quiz_directory: Path) -> Exercise:
    return load_exercise(quiz_directory)


@pytest.fixture
def spec(exercise: Exercise) -> QuizSpec:
    assert isinstance(exercise.spec, QuizSpec)
    return exercise.spec


@pytest.fixture
def grade(tmp_path: Path, exercise: Exercise, spec: QuizSpec) -> Iterator[Grade]:
    """Grade a sheet in a workspace of its own, as `test_katas.py` does.

    Fresh each time because a fix question's run writes `solution.py` and a
    report into the workspace, and a second sheet graded in the same directory
    would start from the first one's leftovers.
    """
    find_git()  # a missing tool fails here, not halfway through provisioning
    provisioner = SubprocessSandboxProvisioner(
        content_root=CONTENT_ROOT, workspace_root=tmp_path / "ws"
    )
    runner = PytestKataRunner()
    counter = itertools.count()
    provisioned = []

    def run(sheet: str) -> Verdict:
        attempt_id = AttemptId.parse(f"{next(counter):08x}-0000-4000-8000-000000000000")
        workspace = provisioner.provision(exercise, attempt_id)
        provisioned.append(workspace)
        return grade_sheet(spec, sheet, runner, workspace)

    yield run
    for workspace in provisioned:
        workspace.dispose()


def _read(directory: Path, name: str) -> str:
    return (directory / name).read_text(encoding="utf-8")


# --- the answers ----------------------------------------------------------


def test_there_are_quizzes() -> None:
    """Parametrising over nothing passes; this is the test that would notice."""
    assert len(QUIZ_DIRECTORIES) >= 8


def test_the_reference_sheet_passes(
    quiz_directory: Path, spec: QuizSpec, grade: Grade
) -> None:
    verdict = grade(_read(quiz_directory, spec.reference))
    failures = [
        f"{report.check_id}: {report.explanation or report.actual}"
        for report in verdict.failures
    ]
    assert not failures, "\n".join(failures)
    assert not verdict.advisories


def test_the_stub_fails_every_question(
    quiz_directory: Path, spec: QuizSpec, grade: Grade
) -> None:
    """A blank sheet passes nothing, and the code it ships fails its suite."""
    verdict = grade(_read(quiz_directory, spec.stub))
    failed = {report.check_id.split("/")[0] for report in verdict.failures}
    assert failed == {question.id for question in spec.questions}


def test_the_sheets_are_in_their_canonical_form(
    quiz_directory: Path, exercise: Exercise, spec: QuizSpec
) -> None:
    """What a solver is handed is what the web form would write."""
    for name in (spec.stub, spec.reference):
        sheet = _read(quiz_directory, name)
        answers = parse_sheet(sheet, spec.questions)
        assert render_sheet(exercise.title, spec.questions, answers) == sheet, name


def test_the_reference_sheet_says_what_the_key_says(
    quiz_directory: Path, spec: QuizSpec
) -> None:
    """Every keyed answer in `solution.md` is the spec's. Not just a passing set."""
    answers = parse_sheet(_read(quiz_directory, spec.reference), spec.questions)
    for question in spec.questions:
        if question.format is not QuestionFormat.FIX:
            assert answers[question.id].values == question.answer, question.id


def test_every_fix_counter_example_fails_exactly_what_it_declares(
    quiz_directory: Path, spec: QuizSpec, grade: Grade
) -> None:
    reference = parse_sheet(_read(quiz_directory, spec.reference), spec.questions)
    for question in spec.fixes:
        assert question.fix is not None
        for example in question.fix.counter_examples:
            answers = dict(reference)
            answers[question.id] = Answer(code=_read(quiz_directory, example.file))
            verdict = grade(render_sheet("counter-example", spec.questions, answers))
            failed = {report.check_id for report in verdict.failures}
            expected = {f"{question.id}/{name}" for name in example.expect_failures}
            assert failed == expected, example.file


# --- the questions --------------------------------------------------------


def test_every_question_carries_its_context(spec: QuizSpec) -> None:
    missing = [question.id for question in spec.questions if question.context is None]
    assert not missing, f"no context: {', '.join(missing)}"


def test_every_quiz_states_its_constraints_hints_and_notes(
    exercise: Exercise, spec: QuizSpec
) -> None:
    assert len(spec.constraints) >= 2
    assert len(exercise.hints) >= 2
    assert exercise.notes.strip()


def test_every_quiz_asks_enough_to_be_an_incident(spec: QuizSpec) -> None:
    """Four questions or more: what happened, why, the fix, and how it is caught."""
    assert len(spec.questions) >= 4


def test_no_option_id_names_its_own_verdict(spec: QuizSpec) -> None:
    giveaways = [
        f"{question.id}.{option.id}"
        for question in spec.questions
        for option in question.options
        if any(word in option.id.split("-") for word in GIVEAWAY_WORDS)
    ]
    assert not giveaways


def test_an_order_question_is_not_listed_in_its_own_order() -> None:
    listed_in_order = [
        question.id
        for question in _questions(QuestionFormat.ORDER)
        if tuple(option.id for option in question.options) == question.answer
    ]
    assert not listed_in_order


def test_the_right_option_is_not_always_in_the_same_place() -> None:
    singles = _questions(QuestionFormat.SINGLE)
    positions = Counter(
        [option.id for option in question.options].index(question.answer[0])
        for question in singles
    )
    most = max(positions.values())
    assert most / len(singles) <= MOST_IN_ONE_POSITION, dict(positions)


def test_the_right_option_is_not_reliably_the_longest_or_the_shortest() -> None:
    """Both ends, because fixing one tell by trimming answers makes the other.

    Phase 25's first draft had the right option strictly longest in 21 of 28
    single-choice questions: the careful, qualified sentence is the one an
    author writes for the answer they believe in. Trimming those answers is
    the fix, and over-trimming would make *shortest* the tell instead.
    """
    singles = _questions(QuestionFormat.SINGLE)
    longest = shortest = 0
    for question in singles:
        right = question.option(question.answer[0])
        assert right is not None
        others = [len(o.text) for o in question.options if o.id != right.id]
        longest += len(right.text) > max(others)
        shortest += len(right.text) < min(others)
    assert longest / len(singles) <= MOST_OFTEN_LONGEST, f"{longest} of {len(singles)}"
    assert shortest / len(singles) <= MOST_OFTEN_LONGEST, (
        f"{shortest} of {len(singles)}"
    )


def test_a_select_all_question_is_not_answered_by_selecting_all() -> None:
    everything = [
        question.id
        for question in _questions(QuestionFormat.MULTIPLE)
        if len(question.answer) == len(question.options)
    ]
    assert not everything
