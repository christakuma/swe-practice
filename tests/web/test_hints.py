"""Progressive hint reveal, in the browser.

`RevealHint`'s own behaviour — the order, the persistence, the refusals — is
covered in `tests/unit/application/`. What only this layer shows is that the panel
appears on both exercise kinds, that a reveal appends and re-renders the counter
out of band, and that a reload shows what was revealed rather than resetting the
ladder.

**The strongest assertion here is the negative one.** A page must not contain a
hint that has not been revealed: that is the whole claim, and it is the one a
template refactor is most likely to break while every positive assertion stays
green.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from practice.domain.ids import AttemptId
    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")

#: A distinctive slice of the fake scenario's only hint, as
#: `tests/fakes/content.py` writes it. A slice rather than the whole sentence,
#: because autoescaping turns its `?` and apostrophes into entities on some paths
#: and this assertion is about presence, not about escaping.
FIRST_WORDS = "What does your teammate"


def a_scenario_attempt(wiring: Wiring) -> AttemptId:
    return wiring.services.start_attempt(SCENARIO).attempt.id


def reveal(client: TestClient, attempt_id: AttemptId) -> str:
    return client.post(f"/api/attempt/{attempt_id}/hint").text


# --- the panel -------------------------------------------------------------


def test_the_prompt_column_offers_a_hint(client: TestClient, wiring: Wiring) -> None:
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "Reveal a hint" in body
    assert f"/api/attempt/{attempt_id}/hint" in body


def test_a_kata_gets_the_same_panel(client: TestClient, wiring: Wiring) -> None:
    """Hints belong to the attempt, not to the exercise kind, which is why this is
    one route and one panel rather than one per kind.
    """
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "Reveal a hint" in body


def test_an_unrevealed_hint_is_not_on_the_page(
    client: TestClient, wiring: Wiring
) -> None:
    """The claim the whole feature rests on. A page that shipped the text and hid
    it with CSS would make the attempt's log describe something nobody did -- and
    Phase 9 reads that log to suggest a grade.
    """
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert FIRST_WORDS not in body


def test_the_panel_says_how_many_are_left(client: TestClient, wiring: Wiring) -> None:
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "1 of 1 left" in body


# --- revealing -------------------------------------------------------------


def test_revealing_returns_the_hint_as_a_fragment(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    fragment = reveal(client, attempt_id)

    assert FIRST_WORDS in fragment
    assert "<!DOCTYPE html>" not in fragment


def test_revealing_numbers_the_hint_within_the_sequence(
    client: TestClient, wiring: Wiring
) -> None:
    """ "hint 1 of 4" is what makes a progressive reveal legible; a bare paragraph
    gives no sense of how much help is left to spend.
    """
    attempt_id = a_scenario_attempt(wiring)

    fragment = reveal(client, attempt_id)

    assert "1 of 1" in fragment


def test_revealing_re_renders_the_control_out_of_band(
    client: TestClient, wiring: Wiring
) -> None:
    """The same two-part response the console uses: one request, two places on the
    page -- the list and the button under it.
    """
    attempt_id = a_scenario_attempt(wiring)

    fragment = reveal(client, attempt_id)

    assert 'id="hint-status"' in fragment
    assert 'hx-swap-oob="true"' in fragment
    assert "All 1 hints revealed" in fragment


def test_the_page_renders_the_control_without_the_out_of_band_flag(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert 'id="hint-status"' in body
    assert "hx-swap-oob" not in body


def test_a_revealed_hint_survives_a_reload(client: TestClient, wiring: Wiring) -> None:
    """Rendered from the event log, like the console transcript, so a reload shows
    what was revealed and a second tab shows it too.
    """
    attempt_id = a_scenario_attempt(wiring)
    reveal(client, attempt_id)

    body = client.get(f"/attempt/{attempt_id}").text

    assert FIRST_WORDS in body


def test_revealing_is_recorded_on_the_attempt(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    reveal(client, attempt_id)

    stored = wiring.attempts.get(attempt_id)
    assert stored is not None
    assert stored.hints_revealed == 1


def test_running_out_is_refused_into_the_list(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)
    reveal(client, attempt_id)

    fragment = reveal(client, attempt_id)

    assert 'class="hint refused"' in fragment
    assert "no hints left" in fragment


def test_a_finished_attempt_refuses_a_reveal(
    client: TestClient, wiring: Wiring
) -> None:
    """A tab left open across a submission, which is the case every mutating path
    on this page has.
    """
    attempt_id = a_scenario_attempt(wiring)
    client.post(f"/api/attempt/{attempt_id}/submit-scenario")

    fragment = reveal(client, attempt_id)

    assert "reveal a hint" in fragment


def test_a_finished_attempt_still_reports_what_was_revealed(
    client: TestClient, wiring: Wiring
) -> None:
    """Which is the number Phase 9 will read, and the one worth seeing beside the
    verdict that it produced.
    """
    attempt_id = a_scenario_attempt(wiring)
    reveal(client, attempt_id)
    client.post(f"/api/attempt/{attempt_id}/submit-scenario")

    body = client.get(f"/attempt/{attempt_id}").text

    assert "1 of 1 hints were" in body
    assert "Reveal a hint" not in body


def test_an_unknown_attempt_is_refused_as_a_fragment(client: TestClient) -> None:
    response = client.post("/api/attempt/00000000-0000-4000-8000-000000000000/hint")

    assert response.status_code == 200
    assert "no attempt with id" in response.text
    assert "<!DOCTYPE html>" not in response.text


def test_a_malformed_attempt_id_is_refused_the_same_way(client: TestClient) -> None:
    response = client.post("/api/attempt/oops/hint")

    assert response.status_code == 200
    assert 'class="hint refused"' in response.text
