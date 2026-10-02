"""`/browse` — the listing, the filters, and the one form that starts an attempt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")


def test_it_lists_the_whole_library_unfiltered(client: TestClient) -> None:
    body = client.get("/browse").text

    assert "Two Sum" in body
    assert "Revert a pushed commit" in body


def test_a_kind_filter_narrows_the_list(client: TestClient) -> None:
    body = client.get("/browse", params={"kind": "kata"}).text

    assert "Two Sum" in body
    assert "Revert a pushed commit" not in body


def test_a_difficulty_filter_narrows_the_list(client: TestClient) -> None:
    body = client.get("/browse", params={"difficulty": "medium"}).text

    assert "Revert a pushed commit" in body
    assert "Two Sum" not in body


def test_a_tag_filter_matches_on_any_one_tag(client: TestClient) -> None:
    """Intersection, not containment — which is `ExerciseFilter.matches`'s rule.

    Asserted here as well as in the domain because the thing being tested is that
    the route hands the domain a filter rather than making its own comparison.
    """
    body = client.get("/browse", params={"tags": "hash-map"}).text

    assert "Two Sum" in body
    assert "Revert a pushed commit" not in body


def test_filters_combine(client: TestClient) -> None:
    response = client.get("/browse", params={"kind": "kata", "difficulty": "medium"})

    assert "Nothing matches" in response.text


def test_a_filter_value_that_names_nothing_is_dropped(client: TestClient) -> None:
    """A query string is edited by hand and shared in links.

    `?kind=kata&difficulty=hrad` shows the katas rather than a validation page
    about the typo. Refusing reads as rigour and behaves as a dead end — and the
    empty-set convention in `ExerciseFilter` is what makes dropping it mean
    exactly "no constraint on that dimension".
    """
    response = client.get("/browse", params={"kind": "kata", "difficulty": "hrad"})

    assert response.status_code == 200
    assert "Two Sum" in response.text


def test_an_unreadable_tag_is_dropped_rather_than_raising(client: TestClient) -> None:
    """`tag()` validates, and a hand-edited URL is where an invalid one arrives."""
    response = client.get("/browse", params={"tags": "NOT A TAG!!"})

    assert response.status_code == 200


def test_the_tag_control_is_built_from_the_library(client: TestClient) -> None:
    """Derived, not configured: a maintained list is a list that goes stale, and
    `practice validate` has no rule that would notice.
    """
    body = client.get("/browse").text

    assert "hash-map" in body
    assert "history" in body


def test_starting_an_attempt_redirects_to_its_workbench(
    client: TestClient, wiring: Wiring
) -> None:
    """303, so the browser follows with a GET whatever it posted.

    The reload bug this avoids is the one a self-rendering form gets for free:
    refreshing the workbench would provision a second workspace and split one
    piece of work across two attempts.
    """
    response = client.post(
        "/attempt", data={"exercise_id": str(KATA)}, follow_redirects=False
    )

    assert response.status_code == 303
    saved = wiring.attempts.active()
    assert len(saved) == 1
    assert response.headers["location"] == f"/attempt/{saved[0].id}"


def test_starting_an_attempt_provisions_a_workspace(
    client: TestClient, wiring: Wiring
) -> None:
    client.post("/attempt", data={"exercise_id": str(KATA)}, follow_redirects=False)

    assert [found for _, found in wiring.provisioner.provisioned]


def test_starting_an_exercise_that_does_not_exist_is_a_page_not_a_traceback(
    client: TestClient,
) -> None:
    response = client.post(
        "/attempt", data={"exercise_id": "katas/not-a-thing"}, follow_redirects=False
    )

    assert response.status_code == 404
    assert "no exercise with id" in response.text
    assert "Browse the library" in response.text


def test_a_malformed_exercise_id_is_a_page_too(client: TestClient) -> None:
    """`ExerciseId` refuses a value with no track in it, and a hand-edited form
    is exactly where one arrives. The reader wants a sentence, not a 500.
    """
    response = client.post(
        "/attempt", data={"exercise_id": "nonsense"}, follow_redirects=False
    )

    assert response.status_code == 404


def test_an_exercise_with_an_open_attempt_offers_resume_rather_than_start(
    client: TestClient, wiring: Wiring
) -> None:
    """Starting a second attempt at the same exercise splits one piece of work.

    Two workspaces, two budgets, and `practice attempts` listing both — so the
    page offers the attempt that already exists.
    """
    started = wiring.services.start_attempt(KATA)

    body = client.get("/browse").text

    assert f'href="/attempt/{started.attempt.id}"' in body
    assert body.count('name="exercise_id"') == 1


def test_an_attempt_whose_workspace_is_gone_does_not_count_as_resumable(
    client: TestClient, wiring: Wiring
) -> None:
    """`can_resume` again: offering a link that cannot work is what it prevents.

    The row falls back to Start, which is the right offer — the stranded attempt
    is listed on the dashboard with the one thing left to do about it.
    """
    started = wiring.services.start_attempt(KATA)
    wiring.provisioner.collect(started.attempt.id)

    body = client.get("/browse").text

    assert f'href="/attempt/{started.attempt.id}"' not in body
    assert body.count('name="exercise_id"') == 2
