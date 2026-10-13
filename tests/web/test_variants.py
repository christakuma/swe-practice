"""Variants in the browser: the version select, the three ways to use it, and
the line on the workbench that says which version came up.

What the web layer adds for a variant is small on purpose (ADR 0028): a select
on the one Start partial, a form field the route resolves to an exercise id
before it does what it always did, and a note above the workbench. An attempt
at a variant is otherwise an attempt, and nothing in `test_workbench.py` or
`test_submit.py` is repeated here for one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.domain.exercise import Variant
from practice.domain.ids import ExerciseId
from tests.fakes import a_kata

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SORTED = ExerciseId("variants/two-sum-sorted")
THREE = ExerciseId("variants/two-sum-three-ways")

TWIST = "The list is sorted & positions count from 1."


@pytest.fixture
def varied(wiring: Wiring) -> Wiring:
    """The stock library, with two variants of its kata."""
    wiring.content.add(
        a_kata(
            exercise_id=SORTED.value,
            title="Two Sum in a Sorted List",
            variant=Variant(of=KATA, twist=TWIST),
        ),
        a_kata(
            exercise_id=THREE.value,
            title="Three Sum",
            variant=Variant(of=KATA, twist="Three numbers instead of two."),
        ),
    )
    return wiring


def _started(wiring: Wiring) -> list[ExerciseId]:
    return [attempt.exercise_id for attempt in wiring.attempts.active()]


# --- the listing ------------------------------------------------------------


@pytest.mark.usefixtures("varied")
def test_a_variant_is_not_a_row_in_browse(client: TestClient) -> None:
    """Offered under its base and never beside it: the library a solver
    browses is the same length it was before the variants were written.
    """
    body = client.get("/browse").text

    assert 'value="katas/two-sum"' in body
    assert 'name="exercise_id" value="variants/' not in body


@pytest.mark.usefixtures("varied")
def test_an_exercise_with_variants_gets_a_version_select(client: TestClient) -> None:
    body = client.get("/browse").text

    assert '<select name="variant">' in body
    assert '<option value="">Standard</option>' in body
    assert "Two Sum in a Sorted List</option>" in body
    assert f'<option value="{THREE}"' in body
    assert '<option value="random">Surprise me</option>' in body


@pytest.mark.usefixtures("varied")
def test_the_standard_version_is_the_first_option_and_so_the_default(
    client: TestClient,
) -> None:
    """No option is marked `selected`, so a browser picks the first -- and the
    first has an empty value, which the route reads as no choice at all.
    """
    select = client.get("/browse").text.split('<select name="variant">')[1]
    options = select.split("</select>")[0]

    assert options.index('value=""') < options.index(SORTED.value)
    assert "selected" not in options


@pytest.mark.usefixtures("varied")
def test_the_twist_is_the_option_s_tooltip_and_is_escaped(client: TestClient) -> None:
    body = client.get("/browse").text

    assert 'title="The list is sorted &amp; positions count from 1."' in body


@pytest.mark.usefixtures("wiring")
def test_an_exercise_without_variants_gets_no_select(client: TestClient) -> None:
    """A select holding only "Standard" is a control that does nothing."""
    assert '<select name="variant">' not in client.get("/browse").text


@pytest.mark.usefixtures("varied")
def test_the_select_is_on_the_dashboard_s_start_control_too(client: TestClient) -> None:
    """One partial, three pages. The select is in the partial and asks a
    template global, so no route had to learn to pass the variants along --
    which is the claim this test is here to hold.
    """
    assert '<select name="variant">' in client.get("/").text


# --- starting -----------------------------------------------------------------


def test_starting_with_no_variant_field_starts_the_standard_version(
    client: TestClient, varied: Wiring
) -> None:
    """What every form sent before variants existed, and still means."""
    client.post("/attempt", data={"exercise_id": KATA.value})

    assert _started(varied) == [KATA]


def test_starting_with_the_select_left_alone_starts_the_standard_version(
    client: TestClient, varied: Wiring
) -> None:
    client.post("/attempt", data={"exercise_id": KATA.value, "variant": ""})

    assert _started(varied) == [KATA]


def test_choosing_a_variant_starts_an_attempt_at_that_variant(
    client: TestClient, varied: Wiring
) -> None:
    response = client.post(
        "/attempt",
        data={"exercise_id": KATA.value, "variant": SORTED.value},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert _started(varied) == [SORTED]


def test_surprise_me_draws_from_every_version(
    client: TestClient, varied: Wiring
) -> None:
    """The standard version is in the draw, first, and the fake picks last."""
    client.post("/attempt", data={"exercise_id": KATA.value, "variant": "random"})

    assert varied.chooser.offered == [(KATA, SORTED, THREE)]
    assert _started(varied) == [THREE]


def test_a_variant_of_something_else_is_refused_and_starts_nothing(
    client: TestClient, varied: Wiring
) -> None:
    response = client.post(
        "/attempt",
        data={"exercise_id": "git/revert-a-pushed-commit", "variant": SORTED.value},
    )

    assert response.status_code == 404
    assert "has no variant called" in response.text
    assert _started(varied) == []


def test_a_variant_can_be_started_in_interview_mode(
    client: TestClient, varied: Wiring
) -> None:
    """The two choices on the form are independent, and the second is the one
    an interviewer's twist is most at home in."""
    client.post(
        "/attempt",
        data={"exercise_id": KATA.value, "variant": SORTED.value, "interview": "1"},
    )

    (attempt,) = varied.attempts.active()
    assert attempt.exercise_id == SORTED
    assert attempt.policy.is_interview


# --- the workbench --------------------------------------------------------------


def test_a_variant_s_workbench_says_what_the_twist_is(
    client: TestClient, varied: Wiring
) -> None:
    """Names the base by its title rather than its id, and gives the twist --
    the first thing to read after a draw, since it is how a solver learns that
    what came up is not the problem they clicked on.
    """
    started = varied.services.start_attempt(SORTED)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert '<p class="variant-note">' in body
    assert "of Two Sum &mdash;" in body
    assert "The list is sorted &amp; positions count from 1." in body
    assert "Two Sum in a Sorted List" in body


def test_a_standard_workbench_says_nothing_about_variants(
    client: TestClient, varied: Wiring
) -> None:
    started = varied.services.start_attempt(KATA)

    assert "variant-note" not in client.get(f"/attempt/{started.attempt.id}").text


def test_a_variant_whose_base_has_gone_still_opens(
    client: TestClient, varied: Wiring
) -> None:
    """An attempt outlives edits to the library. The note keeps the twist and
    drops the name it can no longer look up."""
    started = varied.services.start_attempt(SORTED)
    varied.content.forget(KATA)

    response = client.get(f"/attempt/{started.attempt.id}")

    assert response.status_code == 200
    assert '<p class="variant-note">' in response.text
    assert (
        "&mdash;" not in response.text.split('class="variant-note"')[1].split("</p>")[0]
    )
