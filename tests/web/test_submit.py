"""`POST /api/attempt/{id}/submit` — the fragment that closes an attempt.

Fragment assertions rather than page ones: what comes back is meant to be swapped
into `#verdict` and nothing else, so a response carrying a `<html>` would be the
bug. The grader behind these is the recording fake — what is being tested is the
route, the form parsing and the template, and whether pytest can run a solution is
`tests/e2e/`'s question.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.ids import ExerciseId
from tests.unit.application.helpers import RecordingGrader, a_failing_verdict
from tests.web.conftest import a_wiring, client_for

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SOLUTION = "def two_sum(values, target):\n    return (0, 1)\n"


def submit_url(attempt_id: object) -> str:
    return f"/api/attempt/{attempt_id}/submit"


def test_submitting_returns_the_verdict_as_a_fragment(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    response = client.post(submit_url(started.attempt.id), data={"source": SOLUTION})

    assert response.status_code == 200
    assert "Finds the two positions" in response.text
    # A fragment, not a page. Anything that swapped a layout into `#verdict`
    # would nest the whole app inside itself.
    assert "<html" not in response.text
    assert "swe-practice" not in response.text


def test_the_submitted_source_is_what_gets_graded(
    client: TestClient, wiring: Wiring
) -> None:
    """From the editor, through the attempt's log, to the grader.

    `SubmitSolution` saves the source before grading so a verdict is always
    derived from something persisted; this is the browser end of that path.
    """
    started = wiring.services.start_attempt(KATA)

    client.post(submit_url(started.attempt.id), data={"source": SOLUTION})

    assert wiring.grader.calls[0][0] == SOLUTION


def test_submitting_completes_the_attempt(client: TestClient, wiring: Wiring) -> None:
    started = wiring.services.start_attempt(KATA)

    client.post(submit_url(started.attempt.id), data={"source": SOLUTION})

    assert list(wiring.attempts.active()) == []
    graded = wiring.attempts.get(started.attempt.id)
    assert graded is not None
    assert graded.verdict is not None


def test_a_failing_verdict_renders_its_explanations() -> None:
    """The failures carry their detail; a pass is one line.

    The thing §1 exists to reject is a tool that says what was wrong and not why,
    so the explanation reaching the page is the feature rather than decoration.
    """
    wiring = a_wiring(RecordingGrader(a_failing_verdict()))
    started = wiring.services.start_attempt(KATA)

    with client_for(wiring) as client:
        body = client.post(
            submit_url(started.attempt.id), data={"source": SOLUTION}
        ).text

    assert "fail" in body
    assert "Finds the two positions" in body


def test_both_complexity_axes_are_passed_through(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    client.post(
        submit_url(started.attempt.id),
        data={"source": SOLUTION, "time": "O(n)", "space": "O(n)"},
    )

    graded = wiring.attempts.get(started.attempt.id)
    assert graded is not None
    assert graded.declared_complexity is not None
    assert graded.declared_complexity.time == "O(n)"


def test_half_a_complexity_claim_declares_nothing(
    client: TestClient, wiring: Wiring
) -> None:
    """`ComplexityClaim` refuses to hold one axis (§4.3), so one is dropped.

    Dropped rather than refused, unlike the CLI's flags: the form sends both
    fields on every submission and leaving one blank is the ordinary case, not a
    usage error somebody typed.
    """
    started = wiring.services.start_attempt(KATA)

    response = client.post(
        submit_url(started.attempt.id), data={"source": SOLUTION, "time": "O(n)"}
    )

    assert response.status_code == 200
    graded = wiring.attempts.get(started.attempt.id)
    assert graded is not None
    assert graded.declared_complexity is None


def test_a_second_submission_is_refused_in_the_slot_the_reader_is_watching(
    client: TestClient, wiring: Wiring
) -> None:
    """The double-click case, and why the refusal is a 200.

    htmx does not swap a 4xx response by default, so a refusal sent as one would
    vanish -- the opposite of telling someone what went wrong. The aggregate is
    what refuses; this is only where the sentence lands.
    """
    started = wiring.services.start_attempt(KATA)
    client.post(submit_url(started.attempt.id), data={"source": SOLUTION})

    response = client.post(submit_url(started.attempt.id), data={"source": SOLUTION})

    assert response.status_code == 200
    assert "<html" not in response.text
    assert "completed" in response.text


def test_submitting_to_an_unknown_attempt_is_a_fragment_too(
    client: TestClient,
) -> None:
    response = client.post(
        submit_url("00000000-0000-4000-8000-000000000000"), data={"source": SOLUTION}
    )

    assert response.status_code == 200
    assert "no attempt with id" in response.text


def test_submitting_to_a_malformed_id_does_not_raise(client: TestClient) -> None:
    response = client.post(submit_url("oops"), data={"source": SOLUTION})

    assert response.status_code == 200
    assert "<html" not in response.text


def test_the_page_posts_to_the_route_that_exists(
    client: TestClient, wiring: Wiring
) -> None:
    """The one assertion that ties the two halves together.

    A template with a typo in its URL fails nowhere else: the route's own tests
    pass, the page renders, and the button does nothing. So the URL the page
    carries is the one the attempt is at.
    """
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert submit_url(started.attempt.id) in body


def test_a_finished_attempt_reloads_to_the_same_verdict_it_was_shown(
    client: TestClient, wiring: Wiring
) -> None:
    """One template for both, which is the point of the partial.

    A fragment rendered by the submission and a page rendered by a reload are the
    same file, so the two cannot drift into showing different things about one
    graded attempt.
    """
    started = wiring.services.start_attempt(KATA)
    fragment = client.post(
        submit_url(started.attempt.id), data={"source": SOLUTION}
    ).text

    page = client.get(f"/attempt/{started.attempt.id}").text

    assert fragment.strip() in page
