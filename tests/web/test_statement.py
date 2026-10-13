"""The prompt column of the workbench: a kata's constraints and its examples tab.

Separate from `test_workbench.py`, which is about the states an attempt can be
in. This file is about what a *kata* adds to the left-hand column (ADR 0027),
and about the two kinds that add nothing and must not be drawn as though they
did.

Asserted on the HTML the route returns, which is as far as a tab drawn without
a script can be tested from here: which panel is showing is decided by a radio
input and a CSS sibling selector, so what the server controls is that both
panels are in the page, that the prompt's input is the one marked `checked`,
and that the ids the stylesheet pairs up are the ids the template wrote.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.attempt import AttemptMode
from practice.domain.exercise import Example
from practice.domain.ids import ExerciseId
from tests.fakes import a_kata

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
DRILL = ExerciseId("sql/one-row-per-customer")

CONSTRAINTS = ("2 <= len(numbers) <= 10**5", "Exactly one pair adds up to the target.")

EXAMPLES = (
    Example(
        input="two_sum([2, 7, 11, 15], 9)",
        output="(0, 1)",
        explanation="2 + 7 is 9.",
    ),
    Example(
        input="numbers = [3, 3]\ntwo_sum(numbers, 6)",
        output="(0, 1)",
    ),
)


def _a_stated_kata(wiring: Wiring, *, examples: tuple[Example, ...] = EXAMPLES) -> None:
    """Swap the library's kata for one that states constraints and examples.

    The default kata in `a_wiring` has neither, on purpose: it is what every
    other web test opens, and it is the case the last test here needs.
    """
    wiring.content.replace_with(a_kata(constraints=CONSTRAINTS, examples=examples))


def _workbench(client: TestClient, wiring: Wiring, exercise: ExerciseId) -> str:
    started = wiring.services.start_attempt(exercise)
    return client.get(f"/attempt/{started.attempt.id}").text


# --- the tabs ---------------------------------------------------------------


def test_a_kata_with_examples_gets_a_prompt_tab_and_an_examples_tab(
    client: TestClient, wiring: Wiring
) -> None:
    _a_stated_kata(wiring)

    body = _workbench(client, wiring, KATA)

    # The four ids the stylesheet's `:checked ~` rules pair up. A rename on
    # either side leaves both panels hidden and nothing else failing.
    for anchor in ("tab-prompt", "tab-examples", "panel-prompt", "panel-examples"):
        assert f'id="{anchor}"' in body
    assert '<label for="tab-prompt">Prompt</label>' in body
    assert '<label for="tab-examples">Examples' in body


def test_the_prompt_is_the_tab_showing_when_the_page_loads(
    client: TestClient, wiring: Wiring
) -> None:
    """The examples are the part you go back to, not the part you start with."""
    _a_stated_kata(wiring)

    body = _workbench(client, wiring, KATA)

    assert '<input type="radio" name="statement" id="tab-prompt" checked>' in body
    assert '<input type="radio" name="statement" id="tab-examples">' in body


def test_the_examples_tab_says_how_many_there_are(
    client: TestClient, wiring: Wiring
) -> None:
    _a_stated_kata(wiring)

    body = _workbench(client, wiring, KATA)

    assert '<span class="count">2</span>' in body


def test_each_example_shows_its_input_its_output_and_its_explanation(
    client: TestClient, wiring: Wiring
) -> None:
    _a_stated_kata(wiring)

    body = _workbench(client, wiring, KATA)

    assert "Example 1" in body
    assert "Example 2" in body
    assert "<pre>two_sum([2, 7, 11, 15], 9)</pre>" in body
    assert "<pre>(0, 1)</pre>" in body
    assert "2 + 7 is 9." in body
    # A snippet of more than one line keeps its line break inside one `pre`,
    # which is what makes an in-place function's example readable at all.
    assert "<pre>numbers = [3, 3]\ntwo_sum(numbers, 6)</pre>" in body


def test_an_example_without_an_explanation_draws_no_empty_paragraph(
    client: TestClient, wiring: Wiring
) -> None:
    _a_stated_kata(wiring)

    body = _workbench(client, wiring, KATA)

    assert body.count('class="explanation"') == 1


def test_an_example_is_shown_as_text_and_never_as_markup(
    client: TestClient, wiring: Wiring
) -> None:
    """An example is source, and source is full of angle brackets and quotes.

    `a < b` is an ordinary thing for one to say, and a content pack is somebody
    else's `exercise.yaml` (Phase 16) -- so this is the escaping every other
    string on the page already gets, asserted for the three new places one is
    drawn.
    """
    hostile = Example(
        input='render("<script>alert(1)</script>")',
        output="'<b>bold</b>'",
        explanation="a < b && b > c",
    )
    _a_stated_kata(wiring, examples=(hostile, EXAMPLES[0]))

    body = _workbench(client, wiring, KATA)

    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "<b>bold</b>" not in body
    assert "a &lt; b &amp;&amp; b &gt; c" in body


# --- the constraints --------------------------------------------------------


def test_the_constraints_are_listed_under_the_prompt(
    client: TestClient, wiring: Wiring
) -> None:
    _a_stated_kata(wiring)

    body = _workbench(client, wiring, KATA)

    assert "<h3>Constraints</h3>" in body
    assert "<li>2 &lt;= len(numbers) &lt;= 10**5</li>" in body
    assert "<li>Exactly one pair adds up to the target.</li>" in body
    # In the prompt's panel rather than the examples': a bound is read with
    # the task, before an approach is chosen.
    prompt_panel = body.split('id="panel-prompt"')[1].split('id="panel-examples"')[0]
    assert "<h3>Constraints</h3>" in prompt_panel


def test_the_prompt_is_still_on_the_page_inside_its_tab(
    client: TestClient, wiring: Wiring
) -> None:
    _a_stated_kata(wiring)

    body = _workbench(client, wiring, KATA)

    prompt_panel = body.split('id="panel-prompt"')[1].split('id="panel-examples"')[0]
    assert "add up to the target" in prompt_panel


# --- interview mode ---------------------------------------------------------


def test_an_interview_still_shows_the_examples_and_the_constraints(
    client: TestClient, wiring: Wiring
) -> None:
    """Interview mode withholds *help*, and neither of these is help.

    Hints, the tutor and the own-editor reveal are things a solver asks for.
    The examples and the bounds are the question, and an interview that hid
    them would be asking a different and vaguer one.
    """
    _a_stated_kata(wiring)
    started = wiring.services.start_attempt(KATA, mode=AttemptMode.INTERVIEW)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'id="panel-examples"' in body
    assert "<pre>two_sum([2, 7, 11, 15], 9)</pre>" in body
    assert "<h3>Constraints</h3>" in body


# --- the kinds with nothing to add ------------------------------------------


def test_a_git_scenario_keeps_a_plain_prompt_heading(
    client: TestClient, wiring: Wiring
) -> None:
    """A tab bar holding one tab is a control that does nothing."""
    body = _workbench(client, wiring, SCENARIO)

    assert "<h2>Prompt</h2>" in body
    assert 'id="tab-examples"' not in body
    assert "<h3>Constraints</h3>" not in body


def test_a_sql_drill_keeps_a_plain_prompt_heading(
    client: TestClient, wiring: Wiring
) -> None:
    """Editable like a kata, and not a kata: `is_kata` in the template means
    *has an editor*, which is exactly why the tabs do not hang off it."""
    body = _workbench(client, wiring, DRILL)

    assert "<h2>Prompt</h2>" in body
    assert 'id="tab-examples"' not in body


def test_a_kata_nobody_wrote_examples_for_keeps_the_heading_too(
    client: TestClient, wiring: Wiring
) -> None:
    """Decided by what the exercise states rather than by what kind it is, so a
    draft kata and a pack's kata without examples both draw a page that works.
    """
    body = _workbench(client, wiring, KATA)

    assert "<h2>Prompt</h2>" in body
    assert 'id="tab-examples"' not in body
    assert "add up to the target" in body


def test_a_kata_can_state_constraints_without_showing_examples(
    client: TestClient, wiring: Wiring
) -> None:
    wiring.content.replace_with(a_kata(constraints=CONSTRAINTS))

    body = _workbench(client, wiring, KATA)

    assert "<h2>Prompt</h2>" in body
    assert "<h3>Constraints</h3>" in body
    assert 'id="tab-examples"' not in body
