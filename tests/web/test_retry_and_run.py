"""Submitting again after a failure, stopping, and the Run button -- ADR 0029.

The request was two things: *let me try a solution before submitting it*, and
*don't make a failed submission the end -- log the fail and let me go again*.
These are the routes and fragments that answer it, behind the recording fakes:
what pytest makes of a solution is `tests/integration/kata/test_examples.py`'s
question, and this file's is what comes back into `#verdict`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.domain.exercise import Example
from practice.domain.ids import ExerciseId
from practice.domain.trial import ExampleResult, Trial
from tests.fakes import a_kata, a_trial
from tests.unit.application.helpers import RecordingGrader, a_failing_verdict
from tests.web.conftest import a_wiring, client_for

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
SOLUTION = "def two_sum(values, target):\n    return (0, 1)\n"


@pytest.fixture
def failing() -> Iterator[tuple[TestClient, Wiring]]:
    """The app over a grader that fails everything."""
    wiring = a_wiring(RecordingGrader(a_failing_verdict()))
    with client_for(wiring) as client:
        yield client, wiring


def with_examples(wiring: Wiring) -> Wiring:
    wiring.content.replace_with(
        a_kata(examples=(Example(input="two_sum([1, 2], 3)", output="(0, 1)"),))
    )
    return wiring


# --- a failed submission ------------------------------------------------------


def test_a_failure_says_the_attempt_is_still_open_and_offers_a_way_to_stop(
    failing: tuple[TestClient, Wiring],
) -> None:
    client, wiring = failing
    started = wiring.services.start_attempt(KATA)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION}
    ).text

    assert "Submission 1 did not pass. The attempt is still open" in fragment
    assert "Finds the two positions" in fragment  # the verdict, under it
    assert f'hx-post="/api/attempt/{started.attempt.id}/concede"' in fragment
    # Not the finished block: nothing to schedule until it is over.
    assert 'id="review"' not in fragment


def test_the_second_press_of_submit_is_graded_not_refused(
    failing: tuple[TestClient, Wiring],
) -> None:
    """The message this replaced: *cannot submit: attempt 4fcff95d is completed*."""
    client, wiring = failing
    started = wiring.services.start_attempt(KATA)
    url = f"/api/attempt/{started.attempt.id}/submit"
    client.post(url, data={"source": SOLUTION})

    fragment = client.post(url, data={"source": SOLUTION}).text

    assert "is completed" not in fragment
    assert "Submission 2 did not pass" in fragment
    assert len(wiring.grader.calls) == 2


def test_conceding_returns_the_finished_block_with_its_schedule(
    failing: tuple[TestClient, Wiring],
) -> None:
    client, wiring = failing
    started = wiring.services.start_attempt(KATA)
    client.post(f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION})

    fragment = client.post(f"/api/attempt/{started.attempt.id}/concede").text

    assert 'id="review"' in fragment
    assert "<strong>again</strong>" in fragment
    stored = wiring.attempts.get(started.attempt.id)
    assert stored is not None
    assert not stored.is_active


def test_conceding_an_attempt_that_never_failed_is_refused_in_the_slot(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    fragment = client.post(f"/api/attempt/{started.attempt.id}/concede").text

    assert '<p class="problem">' in fragment
    assert "no failed submission" in fragment


def test_conceding_a_malformed_id_does_not_raise(client: TestClient) -> None:
    response = client.post("/api/attempt/oops/concede")

    assert response.status_code == 200
    assert '<p class="problem">' in response.text


def test_a_reload_shows_the_last_failure_rather_than_an_empty_slot(
    failing: tuple[TestClient, Wiring],
) -> None:
    client, wiring = failing
    started = wiring.services.start_attempt(KATA)
    client.post(f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION})

    page = client.get(f"/attempt/{started.attempt.id}").text

    assert "Submission 1 did not pass" in page
    # Still the editor, because the attempt is still open.
    assert 'id="solution-form"' in page


def test_a_fresh_attempt_reloads_to_an_empty_slot(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    page = client.get(f"/attempt/{started.attempt.id}").text

    assert "did not pass" not in page


def test_a_failed_scenario_keeps_its_console(
    failing: tuple[TestClient, Wiring],
) -> None:
    client, wiring = failing
    started = wiring.services.start_attempt(SCENARIO)

    fragment = client.post(f"/api/attempt/{started.attempt.id}/submit-scenario").text
    page = client.get(f"/attempt/{started.attempt.id}").text

    assert "Submission 1 did not pass" in fragment
    assert 'class="console-form"' in page
    assert "Submission 1 did not pass" in page


def test_the_scenario_confirm_no_longer_says_every_submission_finishes(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(SCENARIO)

    page = client.get(f"/attempt/{started.attempt.id}").text

    assert "A pass finishes the attempt." in page
    assert "This finishes the attempt." not in page


def test_an_unknown_track_is_not_carried_into_the_failed_fragment() -> None:
    """The failed fragment carries the track to the concede post -- but only one
    the library declares, the rule every form here follows."""
    wiring = a_wiring(RecordingGrader(a_failing_verdict()))
    with client_for(wiring) as client:
        started = wiring.services.start_attempt(KATA)
        fragment = client.post(
            f"/api/attempt/{started.attempt.id}/submit",
            data={"source": SOLUTION, "track": "no-such-track"},
        ).text

    # An unknown track is dropped here as everywhere, so the form carries none.
    assert 'name="track"' not in fragment


# --- Run ----------------------------------------------------------------------


def test_run_returns_each_example_and_says_nothing_was_submitted(
    client: TestClient, wiring: Wiring
) -> None:
    with_examples(wiring)
    wiring.examples.trial = a_trial(passing=1, failing=1)
    started = wiring.services.start_attempt(KATA)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/try", data={"source": SOLUTION}
    ).text

    assert "1 of 2 examples gave the expected output. Not submitted." in fragment
    assert '<li class="check passed">' in fragment
    assert '<li class="check failed">' in fragment
    assert "expected 0" in fragment
    assert "got None" in fragment
    assert wiring.examples.calls == [(str(KATA), SOLUTION, False)]


def test_run_records_nothing_on_the_attempt(client: TestClient, wiring: Wiring) -> None:
    with_examples(wiring)
    started = wiring.services.start_attempt(KATA)

    client.post(f"/api/attempt/{started.attempt.id}/try", data={"source": SOLUTION})

    stored = wiring.attempts.get(started.attempt.id)
    assert stored is not None
    assert stored.events == ()
    assert wiring.grader.calls == []


def test_a_run_that_raised_shows_the_exception_and_what_it_printed(
    client: TestClient, wiring: Wiring
) -> None:
    with_examples(wiring)
    wiring.examples.trial = Trial(
        examples=(
            ExampleResult(
                input="two_sum([], 0)",
                expected="(0, 1)",
                error="IndexError: list index out of range",
                stdout="checking []\n",
            ),
        )
    )
    started = wiring.services.start_attempt(KATA)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/try", data={"source": SOLUTION}
    ).text

    assert "raised IndexError: list index out of range" in fragment
    assert '<pre class="trial-stdout">checking []' in fragment


def test_a_run_that_could_not_start_says_why_and_draws_no_rows(
    client: TestClient, wiring: Wiring
) -> None:
    with_examples(wiring)
    wiring.examples.trial = Trial(problem="your solution could not be imported: X")
    started = wiring.services.start_attempt(KATA)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/try", data={"source": SOLUTION}
    ).text

    assert '<p class="problem">your solution could not be imported: X</p>' in fragment
    assert "examples gave the expected output" not in fragment


def test_run_on_a_scenario_is_refused_in_the_slot(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(SCENARIO)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/try", data={"source": "x = 1"}
    ).text

    assert '<p class="problem">' in fragment
    assert "no examples to run" in fragment


def test_the_run_button_is_drawn_for_a_kata_with_examples(
    client: TestClient, wiring: Wiring
) -> None:
    with_examples(wiring)
    started = wiring.services.start_attempt(KATA)

    page = client.get(f"/attempt/{started.attempt.id}").text

    assert 'id="run-examples"' in page
    assert f'"/api/attempt/{started.attempt.id}/try"' in page


def test_no_run_button_without_examples(client: TestClient, wiring: Wiring) -> None:
    """A button that ran nothing would look like a pass."""
    started = wiring.services.start_attempt(KATA)

    page = client.get(f"/attempt/{started.attempt.id}").text

    assert 'id="run-examples"' not in page
