"""A quiz in the browser: the form, the post, and what each fragment says.

The grader here is the real `QuizGrader` over a canned kata runner, rather
than the recording fake the other web tests use, because what a quiz page
shows depends on what the verdict says -- a wrong choice's reason, never the
right one -- and that is the grader's sentence, not a fixture's.
"""

from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING

from practice.adapters.quiz import QuizGrader
from practice.application.registry import GraderRegistry
from practice.domain.attempt import SolutionSaved
from practice.domain.exercise import ExerciseKind
from tests.fakes import StubKataRunner, a_kata, a_quiz, a_record, a_run
from tests.unit.application.helpers import RecordingGrader
from tests.web.conftest import Wiring, client_for

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from practice.composition import Services
    from practice.domain.ids import AttemptId

QUIZ = a_quiz(with_fix=True)

RIGHT = {
    "q:which-line": ["1"],
    "q:which-condition": ["circular-wait"],
    "q:which-checks": ["lock-graph", "lockdep"],
    "q:which-steps": ["add", "copy", "drop"],
    "fix:fix-it": ["def transfer():\r\n    pass\r\n"],
}


class QuizWiring(Wiring):
    """The usual fakes, with the quiz kind graded for real."""

    def __init__(self) -> None:
        super().__init__(exercises=(QUIZ, a_kata()), grader=RecordingGrader())
        self.runner = StubKataRunner(a_run(a_record("test_sorted")))

    @property
    def services(self) -> Services:
        base = super().services
        return dataclasses.replace(
            base,
            graders=GraderRegistry(
                graders={
                    ExerciseKind.QUIZ: QuizGrader(self.runner),
                    ExerciseKind.KATA: self.grader,
                }
            ),
        )


def started() -> tuple[QuizWiring, TestClient, AttemptId]:
    wiring = QuizWiring()
    attempt = wiring.services.start_attempt(QUIZ.id).attempt
    return wiring, client_for(wiring), attempt.id


def field(keyword: str) -> str:
    """`q__which_condition` is the field `q:which-condition`."""
    prefix, _, rest = keyword.partition("__")
    return f"{prefix}:{rest.replace('_', '-')}"


def post(client: TestClient, attempt_id: AttemptId, **changes: list[str]) -> str:
    form = {**RIGHT, **{field(key): value for key, value in changes.items()}}
    assert set(form) == set(RIGHT), "a change names a field the form does not have"
    response = client.post(f"/api/attempt/{attempt_id}/answers", data=form)
    assert response.status_code == 200
    return response.text


def test_the_workbench_draws_a_quiz_as_a_form() -> None:
    _, client, attempt_id = started()
    page = client.get(f"/attempt/{attempt_id}").text

    assert 'id="quiz-form"' in page
    assert 'type="radio" name="q:which-condition" value="circular-wait"' in page
    assert 'type="checkbox" name="q:which-checks" value="lockdep"' in page
    assert page.count('<select name="q:which-steps"') == 3
    assert 'name="q:which-line" value="1"' in page
    assert 'name="fix:fix-it"' in page
    # Each question's context is in front of it, and the incident's
    # constraints are in the prompt column.
    assert "Four conditions." in page
    assert "16 worker threads." in page
    # Nothing on the page says which option is right.
    assert "No cycle can form." not in page
    assert "Open in my editor" not in page


def test_right_answers_pass_and_show_every_explanation() -> None:
    wiring, client, attempt_id = started()
    fragment = post(client, attempt_id)

    assert "The answers" in fragment
    assert "No cycle can form." in fragment
    assert "Only by luck." in fragment
    assert "The source&#39;s lock is taken first." in fragment
    graded = wiring.attempts.get(attempt_id)
    assert graded is not None
    assert graded.verdict is not None
    assert graded.verdict.passed


def test_the_fix_reaches_the_runner_with_unix_line_endings() -> None:
    wiring, client, attempt_id = started()
    post(client, attempt_id)
    assert wiring.runner.sources == ["def transfer():\n    pass"]


def test_the_form_is_saved_as_the_answer_sheet() -> None:
    wiring, client, attempt_id = started()
    post(client, attempt_id)
    attempt = wiring.attempts.get(attempt_id)
    assert attempt is not None
    (saved,) = [event for event in attempt.events if isinstance(event, SolutionSaved)]
    assert "\nwhich-checks: lock-graph, lockdep\n" in saved.source
    assert "\nwhich-steps: add, copy, drop\n" in saved.source


def test_a_wrong_choice_says_why_it_is_wrong_and_not_what_is_right() -> None:
    wiring, client, attempt_id = started()
    fragment = post(client, attempt_id, q__which_condition=["hold-and-wait"])

    assert "did not pass" in fragment
    assert "You chose `hold-and-wait`: Still held." in fragment
    assert "No cycle can form." not in fragment
    assert "The answers" not in fragment
    assert list(wiring.attempts.active())


def test_a_reload_after_a_failure_draws_the_answers_given() -> None:
    _, client, attempt_id = started()
    post(client, attempt_id, q__which_condition=["hold-and-wait"])
    page = client.get(f"/attempt/{attempt_id}").text

    assert re.search(r'value="hold-and-wait"\s+checked', page)
    assert not re.search(r'value="circular-wait"\s+checked', page)
    assert re.search(r'<option value="copy"\s+selected>', page)
    assert "def transfer():" in page
    assert "You chose `hold-and-wait`" in page


def test_a_step_left_on_its_placeholder_is_not_placed() -> None:
    _, client, attempt_id = started()
    fragment = post(client, attempt_id, q__which_steps=["add", "", "drop"])
    assert "`copy` is not placed" in fragment


def test_a_finished_quiz_shows_its_review_on_the_page() -> None:
    _, client, attempt_id = started()
    post(client, attempt_id)
    page = client.get(f"/attempt/{attempt_id}").text
    assert "The answers" in page
    assert "Same idea." in page
    assert 'id="quiz-form"' not in page


def test_posting_answers_to_something_else_is_refused() -> None:
    wiring = QuizWiring()
    attempt = wiring.services.start_attempt(a_kata().id).attempt
    response = client_for(wiring).post(f"/api/attempt/{attempt.id}/answers", data=RIGHT)
    assert "is not a quiz" in response.text


def test_posting_to_an_attempt_that_does_not_exist_is_refused() -> None:
    wiring = QuizWiring()
    response = client_for(wiring).post("/api/attempt/oops/answers", data=RIGHT)
    assert response.status_code == 200
    assert "<html" not in response.text
