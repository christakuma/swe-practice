"""The spoiler boundary, held for every exercise on disk.

`tests/unit/application/test_export_tutor_context.py` proves the boundary on a
fake scenario with one check and one hint. This is the same claim against the
real library, where it matters: an exercise's last hint is usually the command
that solves it, its notes are the lesson written out, and for a git scenario or
a SQL drill the check labels describe the end state one by one. If any of that
reaches the text a solver pastes into a chat while the attempt is open, the
tutor has been handed the answer and asked not to say it.

**Each "is not in the bundle" has an "is in the bundle" beside it, and that pair
is the test.** A needle that never matches cannot fail: if the renderer wrapped a
hint differently from how the exercise stores it, `hint not in text` would pass
for a bundle with every hint printed in it. So the same needles are looked for
in the state where they *should* appear -- a hint once it is revealed, the notes
and the labels once a verdict exists -- and only a needle that is found there
means anything by being absent before (ADR 0022).

**No subprocess, on purpose.** The exercise comes off disk and everything else
is a fake: no fixture runs and no workspace is built, because nothing here is a
question about a repository. That keeps the whole file to a second or two and
off the critical path CLAUDE.md warns about -- `--dist loadfile` puts a file on
one worker, and `test_katas.py` already owns the suite's floor.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import ContentError, load_exercise
from practice.adapters.content.validation import discover
from practice.adapters.persistence import InMemoryAttemptRepository
from practice.application.tutor import as_json, render_markdown
from practice.application.use_cases import ExportTutorContext
from practice.config import content_root
from practice.domain.attempt import Attempt, AttemptPolicy
from practice.domain.exercise import KataSpec
from practice.domain.ids import AttemptId
from practice.domain.verdict import CheckReport, Severity, Verdict
from tests.fakes import (
    BuilderRepoQueryFactory,
    FakeContentRepository,
    FakeProvisioner,
    a_repo,
)

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.exercise import Exercise

CONTENT_ROOT = content_root()

STARTED = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
ATTEMPT = AttemptId.parse("00000000-0000-4000-8000-000000000018")


def _identify(directory: Path) -> str:
    return directory.relative_to(CONTENT_ROOT).as_posix()


def _loadable() -> list[Path]:
    """Every exercise that loads. One that does not is `test_library.py`'s to
    report, and crashing collection here would hide that report.
    """
    found = []
    for directory in sorted(discover(CONTENT_ROOT)):
        try:
            load_exercise(directory)
        except ContentError:
            continue
        found.append(directory)
    return found


EXERCISE_DIRECTORIES = _loadable()


#: Parametrized per kind rather than skipped, which is `test_library.py`'s rule:
#: a skip per non-kata reads fine at three exercises and is noise at a hundred.
KATA_DIRECTORIES = [
    directory
    for directory in EXERCISE_DIRECTORIES
    if isinstance(load_exercise(directory).spec, KataSpec)
]


@pytest.fixture(params=EXERCISE_DIRECTORIES, ids=_identify)
def exercise(request: pytest.FixtureRequest) -> Exercise:
    return load_exercise(request.param)


@pytest.fixture(params=KATA_DIRECTORIES, ids=_identify)
def kata(request: pytest.FixtureRequest) -> Exercise:
    return load_exercise(request.param)


class Session:
    """One open attempt at one real exercise, over fakes for everything else."""

    def __init__(self, exercise: Exercise) -> None:
        self.exercise = exercise
        self.attempts = InMemoryAttemptRepository()
        self.provisioner = FakeProvisioner()
        self.attempt = Attempt(
            attempt_id=ATTEMPT,
            exercise_id=exercise.id,
            policy=AttemptPolicy.for_exercise(exercise),
            started_at=STARTED,
        )
        self.provisioner.provision(exercise, ATTEMPT)
        self.attempts.save(self.attempt)
        self._export = ExportTutorContext(
            content=FakeContentRepository([exercise]),
            attempts=self.attempts,
            provisioner=self.provisioner,
            repo_query=BuilderRepoQueryFactory(a_repo()),
        )

    def bundle(self) -> str:
        """Both renderings, joined: a leak in either one is a leak.

        The JSON is flattened to its string values rather than dumped, because
        `json.dumps` escapes quotes and newlines and a hint holding either would
        then never match itself.
        """
        context = self._export(ATTEMPT)
        return "\n".join([render_markdown(context), *_strings(as_json(context))])

    def reveal_a_hint(self) -> None:
        self.attempt.reveal_next_hint(at=STARTED + timedelta(minutes=1))
        self.attempts.save(self.attempt)

    def grade(self) -> None:
        """Finish the attempt with every check failed.

        Failed, because a failed check is the one whose explanation the verdict
        page prints, so this is the state in which the most of the exercise's
        own text is legitimately on show.
        """
        self.attempt.complete(_failing(self.exercise), at=STARTED + timedelta(hours=1))
        self.attempts.save(self.attempt)


def _strings(value: object) -> list[str]:
    """Every string anywhere inside a JSON-shaped value."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [found for item in value.values() for found in _strings(item)]
    if isinstance(value, list):
        return [found for item in value for found in _strings(item)]
    return []


def _failing(exercise: Exercise) -> Verdict:
    """A verdict over the exercise's own checks, or a stand-in for a kata.

    A kata's checks are its hidden tests and exist only once pytest has run
    them, so there is no label on the exercise to leak and one report stands in.
    """
    spec = exercise.spec
    if isinstance(spec, KataSpec):
        return Verdict(
            reports=(
                CheckReport(
                    check_id="a-test",
                    label="A test in the hidden suite.",
                    severity=Severity.REQUIRED,
                    passed=False,
                ),
            )
        )
    return Verdict(
        reports=tuple(
            CheckReport.from_spec(check, passed=False) for check in spec.checks
        )
    )


def _answers(exercise: Exercise) -> list[str]:
    """The exercise's own text that names the answer, hints aside.

    The notes, and for the two declaratively graded kinds every check's label
    and explanation. Stripped the way the renderer strips them, so the
    comparison is about the words rather than a trailing newline.
    """
    needles = [exercise.notes.strip()]
    spec = exercise.spec
    if not isinstance(spec, KataSpec):
        for check in spec.checks:
            needles.append(check.label)
            if check.explanation:
                needles.append(check.explanation.strip())
    return needles


# --- the walk itself -------------------------------------------------------


def test_the_library_was_found() -> None:
    """Without this, every parametrized test below is vacuously true."""
    assert len(EXERCISE_DIRECTORIES) >= 3


# --- hints ------------------------------------------------------------------


def test_an_open_attempt_shows_no_hint_nobody_revealed(exercise: Exercise) -> None:
    bundle = Session(exercise).bundle()

    leaked = [hint.text for hint in exercise.hints if hint.text in bundle]
    assert leaked == []


def test_a_revealed_hint_is_shown_and_the_ones_after_it_are_not(
    exercise: Exercise,
) -> None:
    """The half that makes the test above mean something: the first hint is
    found verbatim once it is revealed, so its absence beforehand was real.
    """
    session = Session(exercise)
    session.reveal_a_hint()

    bundle = session.bundle()

    first, *rest = exercise.hints
    assert first.text in bundle
    assert [hint.text for hint in rest if hint.text in bundle] == []


# --- notes and checks -------------------------------------------------------


def test_an_open_attempt_shows_none_of_the_exercises_answers(
    exercise: Exercise,
) -> None:
    bundle = Session(exercise).bundle()

    leaked = [needle for needle in _answers(exercise) if needle in bundle]
    assert leaked == []


def test_a_graded_attempt_shows_all_of_them(exercise: Exercise) -> None:
    """The other half, as above: every one of those needles is found once a
    verdict exists, so none of them was absent by never being able to match.
    """
    session = Session(exercise)
    session.grade()

    bundle = session.bundle()

    missing = [needle for needle in _answers(exercise) if needle not in bundle]
    assert missing == []


def test_a_katas_hidden_suite_is_not_reachable_at_all(kata: Exercise) -> None:
    """Belt and braces for the one file that sits in the workspace beside the
    solver's own: the bundle reads the stub and nothing else, even when the
    hidden suite is right there.
    """
    spec = kata.spec
    assert isinstance(spec, KataSpec)
    session = Session(kata)
    workspace = session.provisioner.workspace_for(ATTEMPT)
    workspace.write_file(spec.stub, "def stub(): ...")
    workspace.write_file(spec.tests, "def test_hidden(): assert secret_case()")

    bundle = session.bundle()

    assert "def stub(): ..." in bundle
    assert "secret_case" not in bundle
