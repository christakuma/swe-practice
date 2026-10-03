"""The verdict panel: the summary, the severities, and the explanations.

One template serves the page and the submission response, which is the property
that makes a reload show what the submission showed — so these drive it through
both and assert the second contains the first.

**The case worth most here is a pass with an advisory.** §4.4's whole bet is that
*correct tree, but you rewrote history that was already published* is a sentence
the product can say; a panel that showed a green outcome and then listed the
advisory as a bare label would have graded craft and then declined to explain it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.ids import ExerciseId
from practice.domain.verdict import CheckReport, Severity, Verdict
from tests.unit.application.helpers import RecordingGrader
from tests.web.conftest import a_wiring, client_for

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi.testclient import TestClient

SCENARIO = ExerciseId("git/revert-a-pushed-commit")

PASSED = CheckReport(
    check_id="content-restored",
    label="The committed tree matches the state before the bad commit",
    severity=Severity.REQUIRED,
    passed=True,
)

BLOCKED = CheckReport(
    check_id="fix-published",
    label="The fix is on origin, not just on your machine",
    severity=Severity.REQUIRED,
    passed=False,
    expected="refs/remotes/origin/main == HEAD",
    actual="refs/remotes/origin/main is one commit behind",
    explanation="Until origin/main points at your fix, your teammate still gets "
    "the breakage.",
)

ADVISED = CheckReport(
    check_id="no-force-push",
    label="You did not force-update a shared branch",
    severity=Severity.ADVISORY,
    passed=False,
    explanation="Reaching for --force on a shared branch is the habit this "
    "exercise exists to break.",
)


def graded_with(*reports: CheckReport) -> Iterator[tuple[TestClient, str]]:
    """A client whose grader returns exactly `reports`, and a submitted attempt."""
    wiring = a_wiring(RecordingGrader(Verdict(reports=reports)))
    with client_for(wiring) as client:
        attempt_id = wiring.services.start_attempt(SCENARIO).attempt.id
        yield client, str(attempt_id)


def submit(*reports: CheckReport) -> tuple[str, str]:
    """The submission fragment and the page that follows it, for one verdict."""
    for client, attempt_id in graded_with(*reports):
        fragment = client.post(f"/api/attempt/{attempt_id}/submit-scenario").text
        page = client.get(f"/attempt/{attempt_id}").text
        return fragment, page
    raise AssertionError("the client fixture yielded nothing")


def test_the_panel_counts_the_checks_that_passed() -> None:
    """A verdict with six checks on it is a wall of rows, and the first question is
    always "how close was that?" -- a count answers it before the rows are read.
    """
    fragment, _ = submit(PASSED, BLOCKED, ADVISED)

    assert "1 of 3 checks passed" in fragment


def test_the_count_names_the_advisories_separately() -> None:
    """They are not failures and they are not passes: the goal was met and the way
    it was met has a cost, which is the one distinction §4.4 is built on.
    """
    fragment, _ = submit(PASSED, ADVISED)

    assert "1 advisory" in fragment


def test_an_advisory_row_says_so_rather_than_only_being_a_colour() -> None:
    """Colour alone is not a distinction a screen reader or a printed page keeps."""
    fragment, _ = submit(PASSED, ADVISED)

    assert 'class="severity"' in fragment
    assert "advisory" in fragment


def test_a_failing_check_shows_what_was_expected_and_what_was_found() -> None:
    fragment, _ = submit(PASSED, BLOCKED)

    assert "refs/remotes/origin/main is one commit behind" in fragment


def test_a_failing_check_carries_its_author_s_explanation() -> None:
    fragment, _ = submit(PASSED, BLOCKED)

    assert "your teammate still gets" in fragment


def test_a_pass_with_an_advisory_repeats_the_advisory_with_its_reason() -> None:
    """The Phase 8 change, and the reason this file exists.

    A passing attempt's advisory is the only piece of teaching on the page, and it
    was the one thing rendered without the sentence that teaches.
    """
    fragment, _ = submit(PASSED, ADVISED)

    assert '<p class="outcome pass_with_advisories">' in fragment
    assert fragment.count("habit this exercise exists to break") == 2


def test_a_failure_repeats_the_failures_rather_than_the_advisories() -> None:
    """The outcome is where someone stops reading, so what follows it is what has
    to change next. Listing advisories under a FAIL buries the thing that failed.
    """
    fragment, _ = submit(PASSED, BLOCKED, ADVISED)

    assert '<p class="outcome fail">' in fragment
    breakdown = fragment.split('class="outcome fail"')[1]
    assert "The fix is on origin" in breakdown
    assert "You did not force-update" not in breakdown


def test_a_clean_pass_repeats_nothing() -> None:
    fragment, _ = submit(PASSED)

    assert '<p class="outcome pass">' in fragment
    assert fragment.count("The committed tree matches") == 1


def test_the_page_after_a_submission_shows_what_the_submission_showed() -> None:
    """One template, included by the page and returned by the route -- which is
    what makes this true rather than a coincidence two files have to maintain.
    """
    fragment, page = submit(PASSED, ADVISED)

    assert fragment.strip() in page
