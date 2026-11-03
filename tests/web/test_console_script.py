"""`static/console.js`, executed: history on the arrow keys, completion on Tab.

Run under node against a scripted console, for the reason `in-front.js` is
(`test_in_front_script.py` has the argument, and the CI rule that turns a
missing node into a failure rather than a skip). Grepping the page for
`ArrowUp` would pass with the history walking the wrong way, and the two
behaviours worth a test are both about order: which line Up brings back, and
whether a slow answer lands on top of what you typed since.

Each case is the transcript the page loaded with and a list of steps; the
result is the input's value, and the completion list, after each one.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TypedDict

from practice.interface.web.vendor import static_root
from tests.web.test_in_front_script import NODE, needs_node

pytestmark = needs_node

URL = "/api/attempt/00000000-0000-4000-8000-000000000001/complete"
HARNESS = Path(__file__).with_name("console_harness.js")


class After(TypedDict):
    value: str
    listed: list[str] | None
    prevented: bool
    asked: list[str]


def play(lines: list[str], *steps: tuple[str, object]) -> list[After]:
    assert NODE is not None, "node is required on CI; see test_in_front_script.py"
    case = json.dumps({"lines": lines, "steps": [list(step) for step in steps]})
    done = subprocess.run(  # noqa: S603  (our own harness, our own file)
        [NODE, str(HARNESS), str(static_root() / "console.js"), URL, case],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    played: list[After] = json.loads(done.stdout)
    return played


def values(played: list[After]) -> list[str]:
    return [step["value"] for step in played]


# --- history -------------------------------------------------------------------


def test_up_walks_back_from_the_newest_line_and_stops_at_the_oldest() -> None:
    played = play(
        ["git status", "git log --oneline", "git reflog"],
        ("key", "ArrowUp"),
        ("key", "ArrowUp"),
        ("key", "ArrowUp"),
        ("key", "ArrowUp"),
    )

    assert values(played) == [
        "git reflog",
        "git log --oneline",
        "git status",
        "git status",
    ]
    assert all(step["prevented"] for step in played)


def test_down_past_the_newest_line_gives_back_what_was_being_typed() -> None:
    played = play(
        ["git status", "git reflog"],
        ("type", "git sh"),
        ("key", "ArrowUp"),
        ("key", "ArrowUp"),
        ("key", "ArrowDown"),
        ("key", "ArrowDown"),
    )

    assert values(played) == [
        "git sh",
        "git reflog",
        "git status",
        "git reflog",
        "git sh",
    ]


def test_a_line_run_twice_in_a_row_is_one_step_of_history() -> None:
    played = play(
        ["git log", "git status", "git status"],
        ("key", "ArrowUp"),
        ("key", "ArrowUp"),
    )

    assert values(played) == ["git status", "git log"]


def test_the_line_just_run_is_the_first_thing_up_brings_back() -> None:
    """History is the transcript, so it grows with it and needs no bookkeeping."""
    played = play(
        ["git status"],
        ("key", "ArrowUp"),
        ("ran", "git status"),
        ("type", "git log"),
        ("ran", "git log"),
        ("key", "ArrowUp"),
    )

    assert played[-1]["value"] == "git log"


def test_up_with_no_history_changes_nothing() -> None:
    assert values(play([], ("type", "gi"), ("key", "ArrowUp"))) == ["gi", "gi"]


# --- completion ----------------------------------------------------------------


def test_tab_sends_the_line_and_applies_the_answer() -> None:
    played = play(
        [],
        ("type", "git checkout feat"),
        ("answer", {"line": "git checkout feature/x ", "matches": ["feature/x"]}),
        ("key", "Tab"),
    )

    assert played[-1]["asked"] == ["git checkout feat"]
    assert played[-1]["value"] == "git checkout feature/x "
    assert played[-1]["prevented"]


def test_a_tab_that_makes_no_progress_lists_the_choices() -> None:
    played = play(
        [],
        ("type", "git sta"),
        ("answer", {"line": "git sta", "matches": ["stash", "status"]}),
        ("key", "Tab"),
        ("type", "git stas"),
    )

    assert played[2]["listed"] == ["stash", "status"]
    assert played[3]["listed"] is None


def test_completion_works_on_the_text_before_the_caret() -> None:
    played = play(
        [],
        ("type", "git show ma -- x"),
        ("caret", len("git show ma")),
        ("answer", {"line": "git show main ", "matches": ["main"]}),
        ("key", "Tab"),
    )

    assert played[-1]["asked"] == ["git show ma"]
    assert played[-1]["value"] == "git show main  -- x"


def test_tab_on_an_empty_line_moves_focus_as_tab_always_does() -> None:
    """The way out of the console for someone on a keyboard (WCAG 2.1.2)."""
    played = play([], ("key", "Tab"))

    assert not played[0]["prevented"]
    assert played[0]["asked"] == []


def test_shift_tab_always_moves_focus() -> None:
    played = play([], ("type", "git"), ("key", "Shift+Tab"))

    assert not played[-1]["prevented"]
    assert played[-1]["asked"] == []


def test_escape_closes_the_list() -> None:
    played = play(
        [],
        ("type", "git sta"),
        ("answer", {"line": "git sta", "matches": ["stash", "status"]}),
        ("key", "Tab"),
        ("key", "Escape"),
    )

    assert played[2]["listed"] is not None
    assert played[3]["listed"] is None


def test_an_answer_that_arrives_after_more_typing_is_dropped() -> None:
    played = play(
        [],
        ("type", "git che"),
        ("answer", {"line": "git cherry-pick ", "matches": ["cherry-pick"]}),
        ("tab-then", ["type", "git checkout"]),
    )

    assert played[-1]["asked"] == ["git che"]
    assert played[-1]["value"] == "git checkout"


def test_an_answer_that_arrives_after_up_is_dropped() -> None:
    played = play(
        ["git status"],
        ("type", "git che"),
        ("answer", {"line": "git cherry-pick ", "matches": ["cherry-pick"]}),
        ("tab-then", ["key", "ArrowUp"]),
    )

    assert played[-1]["value"] == "git status"


def test_an_answer_that_arrives_after_the_line_ran_is_dropped() -> None:
    played = play(
        [],
        ("type", "git che"),
        ("answer", {"line": "git cherry-pick ", "matches": ["cherry-pick"]}),
        ("tab-then", ["ran", "git che"]),
    )

    assert played[-1]["value"] == ""
