"""`/attempt/{id}` — the page, in each of the states an attempt can be in."""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.exercise import KataSpec
from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")

STUB = "def two_sum(values, target):\n    ...\n"


def test_the_workbench_shows_the_prompt(client: TestClient, wiring: Wiring) -> None:
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "Two Sum" in body
    assert "add up to the target" in body


def test_a_kata_opens_the_editor_on_its_stub(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    spec = started.exercise.spec
    assert isinstance(spec, KataSpec)
    wiring.provisioner.workspace_for(started.attempt.id).write_file(spec.stub, STUB)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "def two_sum(values, target):" in body
    assert "/static/vendor/codemirror.min.js" in body
    assert "/static/vendor/codemirror-python.min.js" in body


def test_the_editor_mode_comes_from_the_exercise(
    client: TestClient, wiring: Wiring
) -> None:
    """From `KataSpec.language`, not hardcoded.

    Which is the claim §15 question 3 rests on: a second kata language is a
    content change plus a vendored mode file, and nothing in the page.
    """
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'mode: "python"' in body


def test_a_git_scenario_gets_no_editor_and_says_what_is_missing(
    client: TestClient, wiring: Wiring
) -> None:
    """The console is phase 8, and the page says so rather than rendering an
    editor over a repository it cannot edit.
    """
    started = wiring.services.start_attempt(SCENARIO)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "codemirror.min.js" not in body
    assert "phase 8" in body
    assert f"practice resume {started.attempt.id}" in body


def test_a_finished_attempt_shows_its_verdict_instead_of_an_editor(
    client: TestClient, wiring: Wiring
) -> None:
    """The case `OpenWorkbench` exists for: a tab left open across a submission.

    `ResumeAttempt` refuses a finished attempt, correctly, and this URL still has
    to render — with the one thing a finished attempt has left to show.
    """
    started = wiring.services.start_attempt(KATA)
    wiring.services.submit_solution(started.attempt.id, source="def two_sum(): ...")

    response = client.get(f"/attempt/{started.attempt.id}")

    assert response.status_code == 200
    assert "Finds the two positions" in response.text
    assert "codemirror.min.js" not in response.text


def test_an_unknown_attempt_is_a_page_not_a_traceback(client: TestClient) -> None:
    response = client.get("/attempt/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert "no attempt with id" in response.text


def test_a_malformed_id_is_a_404_rather_than_a_validation_error(
    client: TestClient,
) -> None:
    """A `UUID`-typed path parameter would answer 422 with a page about the shape
    of the string. Someone opening `/attempt/oops` wants to be told there is
    nothing there.
    """
    response = client.get("/attempt/oops")

    assert response.status_code == 404


def test_an_attempt_whose_workspace_was_collected_says_to_abandon_it(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    wiring.provisioner.collect(started.attempt.id)

    response = client.get(f"/attempt/{started.attempt.id}")

    assert response.status_code == 404
    assert "abandon it" in response.text


def test_an_attempt_whose_exercise_left_the_library_says_to_abandon_it(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    wiring.content.forget(KATA)

    response = client.get(f"/attempt/{started.attempt.id}")

    assert response.status_code == 404
    assert "no longer in the library" in response.text


def test_the_page_keeps_the_navigation_when_it_refuses(client: TestClient) -> None:
    """A refusal is a place to navigate away from, so it is rendered in the layout.

    A bare error page takes the navigation away at the moment it is most wanted.
    """
    body = client.get("/attempt/oops").text

    assert "swe-practice" in body
    assert 'href="/browse"' in body


def test_opening_the_workbench_records_nothing(
    client: TestClient, wiring: Wiring
) -> None:
    """A page load is not something the solver did in the exercise.

    The process assertions of §6.3 read the event log to decide whether someone
    reached for the reflog; an entry per page view would make every advisory
    check learn to ignore one kind of entry.
    """
    started = wiring.services.start_attempt(KATA)
    before = len(started.attempt.events)

    client.get(f"/attempt/{started.attempt.id}")
    client.get(f"/attempt/{started.attempt.id}")

    reloaded = wiring.attempts.get(started.attempt.id)
    assert reloaded is not None
    assert len(reloaded.events) == before
