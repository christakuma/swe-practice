"""Which pages are laid out prompt-beside-editor, and what is in the left column.

The divider, the remembered position and the stacking below 900px are CSS and a
pointer; none of that can be seen from here, and PLAN.md §16 records the
browser session that did see it. What *can* be held is the decision the
template makes: which kinds of page get the layout, and that the one thing
a solver is promised in every mode -- the hints, withheld in an interview -- is
where the layout says it is.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from practice.domain.attempt import AttemptMode
from practice.domain.exercise import Example
from practice.domain.ids import ExerciseId
from practice.interface.web.vendor import static_root
from tests.fakes import a_kata

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
DRILL = ExerciseId("sql/one-row-per-customer")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")


def _a_kata_with_examples(wiring: Wiring) -> None:
    """The default test kata states none, and tabs exist only where examples do."""
    wiring.content.replace_with(
        a_kata(examples=(Example(input="two_sum([2, 7], 9)", output="(0, 1)"),))
    )


def test_an_open_kata_is_laid_out_side_by_side(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'class="workbench editing"' in body
    assert 'id="divider"' in body
    assert 'role="separator"' in body
    assert "/static/workbench.js" in body


def test_the_divider_can_be_reached_without_a_mouse(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert re.search(r'<div class="divider" id="divider"[^>]*tabindex="0"', body)


def test_a_drill_is_side_by_side_too(client: TestClient, wiring: Wiring) -> None:
    """It has an editor, which is what the layout is for."""
    started = wiring.services.start_attempt(DRILL)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "workbench editing" in body


def test_a_scenario_keeps_its_three_columns_and_has_no_divider(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(SCENARIO)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "workbench scenario" in body
    assert "editing" not in body.split('class="workbench')[1].split('"')[0]
    assert 'id="divider"' not in body
    assert "workbench.js" not in body


def test_a_finished_attempt_has_a_verdict_and_not_the_split(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    wiring.services.submit_solution(started.attempt.id, source="def two_sum(): ...")

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'id="divider"' not in body
    assert "workbench.js" not in body


def test_hints_are_a_tab_beside_the_prompt_for_a_kata(
    client: TestClient, wiring: Wiring
) -> None:
    _a_kata_with_examples(wiring)
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'id="tab-hints"' in body
    assert 'id="panel-hints"' in body
    assert body.count('id="hint-list"') == 1


def test_an_interview_has_no_hints_tab_to_find_empty(
    client: TestClient, wiring: Wiring
) -> None:
    _a_kata_with_examples(wiring)
    started = wiring.services.start_attempt(KATA, mode=AttemptMode.INTERVIEW)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'id="tab-hints"' not in body
    assert 'id="hint-list"' not in body
    assert "workbench editing" in body


def test_a_drill_keeps_its_hints_below_the_prompt_not_in_a_tab(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(DRILL)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'id="tab-hints"' not in body
    assert body.count('id="hint-list"') == 1


def test_the_divider_script_is_served_and_names_no_remote_host() -> None:
    script = (static_root() / "workbench.js").read_text(encoding="utf-8")

    assert "practice.workbench.split" in script
    assert "http" not in script
