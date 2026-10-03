"""The schedule block: what it offers, what it writes, and what it refuses.

The control that fills the queue, so the thing worth proving is the loop — a
graded attempt offers a grade, a press stores a card, and the card is the one the
scheduler returned. The scheduler behind these is `FixedScheduler`, which records
the grade it was handed, so a test about *which* grade the page sent does not also
depend on SM-2's intervals.

Fragment assertions, as everywhere in this directory: the response is swapped into
`#review` and a layout in it would nest the app inside itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.ids import ExerciseId
from practice.domain.review import Grade
from tests.unit.application.helpers import RecordingGrader, a_failing_verdict
from tests.web.conftest import a_wiring, client_for

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
SOLUTION = "def two_sum(values, target):\n    return (0, 1)\n"


def review_url(attempt_id: object) -> str:
    return f"/api/attempt/{attempt_id}/review"


def a_graded_attempt(client: TestClient, wiring: Wiring) -> str:
    """Start a kata and submit it through the app, so there is a card to move."""
    started = wiring.services.start_attempt(KATA)
    client.post(f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION})
    return str(started.attempt.id)


# --- what the verdict comes back with --------------------------------------


def test_the_submission_offers_a_grade(client: TestClient, wiring: Wiring) -> None:
    """One response carries both: the verdict for the attempt that ended and the
    control for the next one. A second request to find out what to press would
    make the schedule something the page does after, rather than part of it.
    """
    started = wiring.services.start_attempt(KATA)

    response = client.post(
        f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION}
    )

    assert 'id="review"' in response.text
    assert "Suggested" in response.text
    assert "<html" not in response.text


def test_the_scenario_submission_offers_one_too(
    client: TestClient, wiring: Wiring
) -> None:
    """Scheduling belongs to the attempt, not to the exercise kind, which is why
    both submit routes return the same fragment.
    """
    started = wiring.services.start_attempt(SCENARIO)

    response = client.post(f"/api/attempt/{started.attempt.id}/submit-scenario")

    assert 'id="review"' in response.text
    assert "Suggested" in response.text


def test_a_clean_pass_is_offered_as_easy(client: TestClient, wiring: Wiring) -> None:
    started = wiring.services.start_attempt(KATA)

    response = client.post(
        f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION}
    )

    assert "<strong>easy</strong>" in response.text
    assert "passed clean" in response.text


def test_a_failure_is_offered_as_again_and_says_why() -> None:
    """Its own wiring, because the grader has to be chosen before the client is
    built -- one swapped afterwards would make every test here order-dependent.
    """
    wiring = a_wiring(RecordingGrader(a_failing_verdict()))
    with client_for(wiring) as failing:
        attempt_id = a_graded_attempt(failing, wiring)
        response = failing.get(f"/attempt/{attempt_id}")

    assert "<strong>again</strong>" in response.text
    assert "did not pass" in response.text


def test_a_revealed_hint_shows_up_in_the_reason(
    client: TestClient, wiring: Wiring
) -> None:
    """The log is why `RevealHint` is a use case and not a page property: the
    suggestion reads it, and "passed with a hint" is a different outcome.
    """
    started = wiring.services.start_attempt(KATA)
    client.post(f"/api/attempt/{started.attempt.id}/hint")

    response = client.post(
        f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION}
    )

    assert "<strong>good</strong>" in response.text
    assert "1 hint revealed" in response.text


def test_every_grade_is_a_button_and_the_suggested_one_is_marked(
    client: TestClient, wiring: Wiring
) -> None:
    """Four from the enum, not four strings in the template -- a fifth bucket
    would appear here rather than be missed.
    """
    started = wiring.services.start_attempt(KATA)

    response = client.post(
        f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION}
    )

    for grade in Grade:
        assert f'"grade": "{grade.value}"' in response.text
    assert 'class="grade quiet suggested"' in response.text
    # `quiet` on all four, not only on the three that are not suggested: the
    # default button here is an accent fill, and accenting the suggested one on
    # top of it left it with no visible label at all.
    assert response.text.count('class="grade quiet') == len(Grade)


# --- pressing it -----------------------------------------------------------


def test_pressing_a_grade_stores_the_card(client: TestClient, wiring: Wiring) -> None:
    attempt_id = a_graded_attempt(client, wiring)

    response = client.post(review_url(attempt_id), data={"grade": "hard"})

    assert response.status_code == 200
    assert wiring.scheduler.grades == [Grade.HARD]
    card = wiring.reviews.get_card(KATA)
    assert card is not None
    assert "Next due" in response.text
    assert card.due_on.isoformat() in response.text


def test_pressing_with_no_grade_applies_the_suggestion(
    client: TestClient, wiring: Wiring
) -> None:
    """`grade=None` meaning *use the suggestion* is what lets one surface offer a
    single button and another offer four without the rule being computed twice.
    """
    attempt_id = a_graded_attempt(client, wiring)

    client.post(review_url(attempt_id), data={})

    assert wiring.scheduler.grades == [Grade.EASY]


def test_a_grade_that_is_not_one_of_the_four_falls_back_to_the_suggestion(
    client: TestClient, wiring: Wiring
) -> None:
    """Nothing on the page can send one, so a 422 about it would be an error page
    for a string nobody typed. `routes/browse.py` drops an unknown filter value
    for the same reason.
    """
    attempt_id = a_graded_attempt(client, wiring)

    response = client.post(review_url(attempt_id), data={"grade": "brilliant"})

    assert response.status_code == 200
    assert wiring.scheduler.grades == [Grade.EASY]


def test_an_override_is_reported_as_one(client: TestClient, wiring: Wiring) -> None:
    """An override is the only feedback the suggestion rule will ever get, so the
    response says that one happened rather than quietly applying it.
    """
    attempt_id = a_graded_attempt(client, wiring)

    response = client.post(review_url(attempt_id), data={"grade": "again"})

    assert "overriding the suggested" in response.text
    assert "<em>easy</em>" in response.text


def test_the_response_is_the_block_and_not_a_page(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_graded_attempt(client, wiring)

    response = client.post(review_url(attempt_id), data={"grade": "good"})

    assert response.text.lstrip().startswith("<section")
    assert "<html" not in response.text


# --- what it refuses -------------------------------------------------------


def test_a_second_press_is_refused_in_the_block(
    client: TestClient, wiring: Wiring
) -> None:
    """A double-click, a refresh, or a tab left open. The refusal lands in the
    block the reader is looking at, at status 200 -- htmx does not swap a 4xx, so
    one sent that way would vanish.
    """
    attempt_id = a_graded_attempt(client, wiring)
    client.post(review_url(attempt_id), data={"grade": "good"})

    response = client.post(review_url(attempt_id), data={"grade": "easy"})

    assert response.status_code == 200
    assert "already been reviewed" in response.text
    assert len(wiring.scheduler.calls) == 1


def test_an_attempt_still_running_cannot_be_scheduled(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    response = client.post(review_url(started.attempt.id), data={"grade": "good"})

    assert "no verdict to grade" in response.text
    assert len(wiring.reviews) == 0


def test_an_id_nothing_resolves_is_refused_in_the_block(client: TestClient) -> None:
    response = client.post(review_url("not-a-uuid"), data={"grade": "good"})

    assert response.status_code == 200
    assert 'id="review"' in response.text


# --- the page that survives a reload ---------------------------------------


def test_reloading_a_graded_attempt_shows_the_same_offer(
    client: TestClient, wiring: Wiring
) -> None:
    """The property `partials/graded.html` exists for: the page and the
    submission render the same file, so a reload cannot show less.
    """
    attempt_id = a_graded_attempt(client, wiring)

    page = client.get(f"/attempt/{attempt_id}")

    assert 'id="review"' in page.text
    assert "Suggested" in page.text


def test_reloading_after_scheduling_says_it_is_already_done(
    client: TestClient, wiring: Wiring
) -> None:
    """Shown before it is pressed as well as refused after, from one property on
    the DTO -- so what the page offers and what the post accepts cannot disagree.
    """
    attempt_id = a_graded_attempt(client, wiring)
    client.post(review_url(attempt_id), data={"grade": "good"})

    page = client.get(f"/attempt/{attempt_id}")

    assert "Already scheduled" in page.text
    assert "grade" not in page.text.split('id="review"')[1].split("</section>")[0]


def test_an_attempt_still_running_has_no_schedule_block(
    client: TestClient, wiring: Wiring
) -> None:
    """`OfferReview` refuses an attempt with no verdict, so the page does not ask
    -- the template branches on the same question rather than catching the error.
    """
    started = wiring.services.start_attempt(KATA)

    page = client.get(f"/attempt/{started.attempt.id}")

    assert 'id="review"' not in page.text
