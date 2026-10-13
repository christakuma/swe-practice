"""`static/in-front.js`, executed -- not found in a page.

The workbench reports which attempt is in front of the solver (ADR 0026), and
the whole of the two-tab guarantee is in which events that script listens to
and what it does on each. A test that greps the page for `visibilitychange`
passes with the listener attached to the wrong object, and passed for a version
that had no answer to the back button at all. So this runs the file as it is
served, under node, against a document that is a script of events.

**Node, and skipped without it -- except under CI, where it fails.** There is
no JavaScript engine in the dependency set and one is not worth adding for
forty lines. A skip on somebody's laptop is a machine that cannot check, which
is honest. A skip on the runner is nine tests quietly leaving the gate: the
first version of this file said "node is on both CI images" and nothing held
that, so an image that dropped it would have turned the whole file grey under
a green build. `may_skip` is the difference, and the last two tests are about
it rather than about the script.

The page's half (`test_workbench.py`: the tag is there, on an open attempt,
pointing at this attempt's endpoint) needs no node at all.

Each case is a starting visibility and a list of steps, and the expected value
is **how many reports had been sent after each step** -- so a case says where
in the sequence a report belongs, not only that one happened eventually.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import pytest

from practice.interface.web.vendor import static_root

if TYPE_CHECKING:
    from collections.abc import Mapping

NODE = shutil.which("node")


def may_skip(node: str | None, environ: Mapping[str, str]) -> bool:
    """Whether having no node is a reason to skip rather than to fail.

    Only off the runner. GitHub Actions sets `CI`, and so does nearly every
    other one; with it set and no node, the tests run and fail in `run`, naming
    what is missing.
    """
    return node is None and not environ.get("CI")


needs_node = pytest.mark.skipif(
    may_skip(NODE, os.environ), reason="needs node to run the script"
)

URL = "/api/attempt/00000000-0000-4000-8000-000000000001/current"

#: The scripted document: listeners, one property, and a `fetch` that records.
HARNESS = Path(__file__).with_name("in_front_harness.js")


class Played(TypedDict):
    """What the harness prints: the running totals, and every request made."""

    counts: list[int]
    posts: list[list[str]]
    unhandled: list[str]


def run(visibility: str, *steps: tuple[str, object]) -> Played:
    """Load the script into a tab that starts `visibility`, then play `steps`.

    `counts[0]` is how many reports the load itself sent; `counts[n]` is the
    running total after step `n`.
    """
    assert NODE is not None, (
        "node is not on PATH, and CI is set: these tests are the only thing "
        "that runs static/in-front.js, so here they fail rather than skip"
    )
    done = subprocess.run(  # noqa: S603  (node, on two files in this repository)
        [
            NODE,
            str(HARNESS),
            str(static_root() / "in-front.js"),
            visibility,
            URL,
            json.dumps(steps),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    result: Played = json.loads(done.stdout)
    assert result["unhandled"] == []
    return result


HIDE = ("visibility", "hidden")
SHOW = ("visibility", "visible")
FOCUS = ("focus", None)
BLUR = ("blur", None)


@needs_node
def test_a_visible_tab_reports_once_when_it_loads() -> None:
    result = run("visible")

    assert result["counts"] == [1]
    assert result["posts"] == [[URL, "POST"]]


@needs_node
def test_a_tab_opened_in_the_background_says_nothing_until_it_is_looked_at() -> None:
    """A page loaded is not a page looked at: a link opened in a new tab must
    not take the mark from the attempt on screen.
    """
    result = run("hidden", SHOW)

    assert result["counts"] == [0, 1]


@needs_node
def test_switching_to_the_tab_is_one_report_though_it_is_two_events() -> None:
    """The browser fires `visibilitychange` and then gives the window focus.
    The first version sent a request for each.
    """
    result = run("visible", HIDE, BLUR, SHOW, FOCUS)

    assert result["counts"] == [1, 1, 1, 2, 2]


@needs_node
def test_the_order_of_those_two_events_does_not_matter() -> None:
    result = run("visible", BLUR, HIDE, FOCUS, SHOW)

    assert result["counts"] == [1, 1, 1, 1, 2]


@needs_node
def test_returning_to_the_window_reports_though_the_tab_stayed_visible() -> None:
    """Two windows side by side, or a return from a terminal where `practice
    resume` moved the mark: the tab never stopped being visible, so
    `visibilitychange` cannot be what says it is in front again.
    """
    result = run("visible", BLUR, FOCUS, FOCUS)

    assert result["counts"] == [1, 1, 2, 2]


@needs_node
def test_a_page_restored_by_the_back_button_reports() -> None:
    """The back/forward cache reruns no script and changes neither visibility
    nor focus, so without `pageshow` the attempt on screen is not the current
    one. An ordinary `pageshow` -- every first load fires one -- is not a
    second report.
    """
    result = run("visible", ("pageshow", False), ("pageshow", True))

    assert result["counts"] == [1, 1, 2]


@needs_node
def test_a_refusal_ends_the_reports_for_good() -> None:
    """The attempt was submitted from this page. Every later return to the tab
    used to collect another 409; now the first one is the last request.
    """
    result = run(
        "visible",
        ("answer", 409),
        BLUR,
        FOCUS,
        BLUR,
        FOCUS,
        HIDE,
        SHOW,
        ("pageshow", True),
    )

    assert result["counts"] == [1, 1, 1, 2, 2, 2, 2, 2, 2]


@needs_node
def test_an_attempt_that_is_gone_ends_them_too() -> None:
    result = run("visible", ("answer", 404), BLUR, FOCUS, BLUR, FOCUS)

    assert result["counts"] == [1, 1, 1, 2, 2, 2]


@needs_node
def test_a_server_that_is_not_there_is_tried_again_and_never_thrown() -> None:
    """A stopped server is not a reason to stop for good -- it comes back --
    and not a reason for an unhandled rejection in the console each time, which
    `run` asserts on every case and this is the one that could fail it.
    """
    result = run(
        "visible",
        ("answer", "down"),
        BLUR,
        FOCUS,
        FOCUS,
        ("answer", 204),
        FOCUS,
        FOCUS,
    )

    assert result["counts"] == [1, 1, 1, 2, 3, 3, 4, 4]


# --- and the skip itself -----------------------------------------------------


def test_without_node_it_skips_on_a_laptop_and_not_on_the_runner() -> None:
    """Not decorated, so it runs wherever the others do not."""
    assert may_skip(None, {}) is True
    assert may_skip(None, {"CI": ""}) is True
    assert may_skip(None, {"CI": "true"}) is False


def test_with_node_nothing_is_skipped_anywhere() -> None:
    assert may_skip("/usr/bin/node", {}) is False
    assert may_skip("/usr/bin/node", {"CI": "true"}) is False
