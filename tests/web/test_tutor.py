"""The "Ask an AI" panel, in the browser.

What the bundle *says* is the renderer's business and what it leaves out is the
use case's; both are covered in `tests/unit/application/`. What only this layer
shows is where the panel is drawn and where it is not, that the endpoint returns
a fragment a browser can copy from, and that the editor's contents reach the
bundle when they are sent.

**The negative assertions are the strong ones here too**, as in
`test_hints.py`: the fragment must not carry a hint nobody revealed, and an open
interview must not carry the panel at all.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from practice.application.tutor import TUTOR_PROMPT
from practice.domain.attempt import AttemptMode, CommandResult
from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from practice.domain.ids import AttemptId
    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")

#: A slice of the fake scenario's only hint, as in `test_hints.py`.
HINT_WORDS = "What does your teammate"

#: The fake scenario's notes and its one check, which are the answer.
NOTES = "Why revert and not reset."
CHECK_LABEL = "The bad commit is still reachable."


def a_scenario_attempt(
    wiring: Wiring, *, mode: AttemptMode = AttemptMode.PRACTICE
) -> AttemptId:
    return wiring.services.start_attempt(SCENARIO, mode=mode).attempt.id


def _printed(text: str) -> CommandResult:
    """A command that succeeded and wrote `text` to stdout."""
    return CommandResult(exit_code=0, stdout=text)


def prepare(client: TestClient, attempt_id: AttemptId, **form: str) -> str:
    """The fragment, with entities decoded: what the textarea would hold."""
    response = client.post(f"/api/attempt/{attempt_id}/context", data=form)
    assert response.status_code == 200
    return html.unescape(response.text)


# --- the panel -------------------------------------------------------------


def test_the_prompt_column_offers_the_tutor(client: TestClient, wiring: Wiring) -> None:
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "Ask an AI" in body
    assert f"/api/attempt/{attempt_id}/context" in body
    assert "not recorded" in body


def test_a_kata_gets_the_same_panel(client: TestClient, wiring: Wiring) -> None:
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "Ask an AI" in body


def test_the_page_itself_carries_no_bundle(client: TestClient, wiring: Wiring) -> None:
    """Built on request, not shipped with the page: a transcript in the HTML of
    every workbench load would be a transcript nobody asked for.
    """
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert 'id="tutor-text"' not in body
    assert "You are a tutor" not in body


def test_an_open_interview_does_not_draw_the_panel(
    client: TestClient, wiring: Wiring
) -> None:
    """Withdrawn rather than left to fail, and the banner says so."""
    attempt_id = a_scenario_attempt(wiring, mode=AttemptMode.INTERVIEW)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "Ask an AI" not in body
    assert f"/api/attempt/{attempt_id}/context" not in body
    assert "no tutor" in body


def test_a_finished_interview_draws_it_again(
    client: TestClient, wiring: Wiring
) -> None:
    """The mode withholds help during the attempt, not a post-mortem after it."""
    attempt_id = a_scenario_attempt(wiring, mode=AttemptMode.INTERVIEW)
    wiring.services.submit_scenario(attempt_id)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "Ask an AI" in body


# --- the bundle ------------------------------------------------------------


def test_preparing_returns_the_bundle_in_a_textarea(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    response = client.post(f"/api/attempt/{attempt_id}/context")

    assert response.status_code == 200
    assert "<!DOCTYPE html>" not in response.text
    assert '<textarea id="tutor-text"' in response.text
    assert 'id="tutor-copy"' in response.text
    assert "<script" not in response.text


def test_the_bundle_is_the_prompt_and_the_attempt(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)
    wiring.services.run_scenario_command(attempt_id, "git status")

    text = prepare(client, attempt_id)

    assert TUTOR_PROMPT in text
    assert "# Revert a pushed commit" in text
    assert "**1.** Ran `git status` (exit 0)" in text


def test_the_bundle_is_escaped_on_the_way_into_the_page(
    client: TestClient, wiring: Wiring
) -> None:
    """Command output is untrusted text, and this fragment is mostly command
    output: a `</textarea>` printed by a command must not close the element.
    """
    attempt_id = a_scenario_attempt(wiring)
    wiring.provisioner.workspace_for(attempt_id).result = _printed(
        "</textarea><script>alert(1)</script>"
    )
    wiring.services.run_scenario_command(attempt_id, "cat notes.txt")

    response = client.post(f"/api/attempt/{attempt_id}/context")

    assert "<script>alert(1)</script>" not in response.text
    assert "</textarea><script>" in html.unescape(response.text)


def test_an_open_attempts_bundle_gives_nothing_away(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    text = prepare(client, attempt_id)

    assert HINT_WORDS not in text
    assert NOTES not in text
    assert CHECK_LABEL not in text


def test_a_revealed_hint_is_in_it(client: TestClient, wiring: Wiring) -> None:
    attempt_id = a_scenario_attempt(wiring)
    client.post(f"/api/attempt/{attempt_id}/hint")

    assert HINT_WORDS in prepare(client, attempt_id)


def test_a_graded_attempts_bundle_is_a_post_mortem(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)
    wiring.services.submit_scenario(attempt_id)

    text = prepare(client, attempt_id)

    assert "## The verdict" in text
    assert NOTES in text


def test_the_editors_contents_reach_the_bundle(
    client: TestClient, wiring: Wiring
) -> None:
    """The reason this is a POST: the solution lives in the browser until it is
    submitted, and the file in the workspace is still the stub.
    """
    started = wiring.services.start_attempt(KATA)
    wiring.provisioner.workspace_for(started.attempt.id).write_file(
        "stub.py", "the untouched stub"
    )

    text = prepare(client, started.attempt.id, source="def two_sum(): return 1")

    assert "def two_sum(): return 1" in text
    assert "the untouched stub" not in text


def test_with_no_source_sent_a_kata_falls_back_to_the_file(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    wiring.provisioner.workspace_for(started.attempt.id).write_file(
        "stub.py", "the untouched stub"
    )

    assert "the untouched stub" in prepare(client, started.attempt.id)


def test_preparing_records_nothing(client: TestClient, wiring: Wiring) -> None:
    attempt_id = a_scenario_attempt(wiring)

    prepare(client, attempt_id)
    prepare(client, attempt_id)

    attempt = wiring.attempts.get(attempt_id)
    assert attempt is not None
    assert attempt.events == ()


# --- what it refuses -------------------------------------------------------


def test_an_open_interview_is_refused_as_a_fragment(
    client: TestClient, wiring: Wiring
) -> None:
    """The page does not draw the button, so this is a request somebody wrote
    by hand -- and it gets the sentence, in the slot, at 200 like every refusal.
    """
    attempt_id = a_scenario_attempt(wiring, mode=AttemptMode.INTERVIEW)

    response = client.post(f"/api/attempt/{attempt_id}/context")

    assert response.status_code == 200
    assert "interview mode withholds the tutor" in response.text
    assert "tutor-text" not in response.text


def test_a_malformed_id_is_refused_as_a_fragment(client: TestClient) -> None:
    response = client.post("/api/attempt/oops/context")

    assert response.status_code == 200
    assert "not a valid attempt id" in response.text


def test_a_request_from_another_origin_is_refused(
    bare_client: TestClient, wiring: Wiring
) -> None:
    """What being a POST buys: a transcript of what somebody ran is not
    something another page in the same browser gets to ask for.
    """
    attempt_id = a_scenario_attempt(wiring)

    response = bare_client.post(f"/api/attempt/{attempt_id}/context")

    assert response.status_code == 403
