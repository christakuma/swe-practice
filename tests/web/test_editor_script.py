"""`static/editor.js`, executed -- what it configures and how its handle behaves.

Typing in a real editor cannot be seen from Python, and Phase 27 says so out
loud: the browser session is recorded in PLAN.md §16. What *can* be held down is
everything the script decides before Monaco takes over, and those are the
decisions earlier editors got wrong: whether Tab inserts spaces, whether
brackets close, whether the textarea a form serialises follows the document,
and whether a page whose editor never loaded is still a page.

Run under node for the reason `test_in_front_script.py` gives, with the same
rule about CI: skipped where there is no node on a laptop, a failure on the
runner.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from practice.interface.web.vendor import static_root

NODE = shutil.which("node")

needs_node = pytest.mark.skipif(
    NODE is None and not os.environ.get("CI"), reason="needs node to run the script"
)

HARNESS = Path(__file__).with_name("editor_harness.js")

STUB = "def f():\n    pass\n"


def run(scenario: str) -> dict[str, Any]:
    assert NODE is not None, "node is required to run the editor script"
    done = subprocess.run(  # noqa: S603  (node, on two files in this repository)
        [NODE, str(HARNESS), str(static_root() / "editor.js"), scenario],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    result: dict[str, Any] = json.loads(done.stdout)
    return result


@needs_node
def test_the_handle_answers_from_the_textarea_before_monaco_arrives() -> None:
    result = run("default")

    assert result["hasHandle"] is True
    assert result["beforeReady"] == STUB
    assert result["textareaAfterSet"] == "x = 1\n"


@needs_node
def test_the_editor_is_configured_for_a_practice_session() -> None:
    options = run("default")["options"]

    assert options["language"] == "python"
    assert options["tabSize"] == 4
    assert options["insertSpaces"] is True
    assert options["detectIndentation"] is False
    assert options["autoIndent"] == "full"
    assert options["autoClosingBrackets"] == "always"
    assert options["autoClosingQuotes"] == "always"
    assert options["matchBrackets"] == "always"
    assert options["quickSuggestions"] is False
    assert options["automaticLayout"] is True
    assert options["theme"] == "practice"


@needs_node
def test_yaml_indents_by_two_and_everything_else_by_four() -> None:
    assert run("yaml")["options"]["tabSize"] == 2


@needs_node
def test_the_textarea_follows_the_document_so_a_form_needs_no_script() -> None:
    result = run("default")

    assert result["textareaHidden"] is True
    assert result["textareaFollows"] == "typed"
    assert "is-monaco" in result["classes"]


@needs_node
def test_the_document_is_lf_whatever_the_platform_defaults_to() -> None:
    """Found by typing into it on Windows, where Monaco's default is CRLF."""
    result = run("default")

    assert result["eol"] == 0
    assert result["lineEnding"] == "\n"


@needs_node
def test_ctrl_enter_presses_run_and_a_disabled_run_ignores_it() -> None:
    result = run("default")

    assert result["commandKeys"] == 2048 | 3
    assert result["runClicks"] == 1


@needs_node
def test_a_mirror_editor_can_be_made_read_only() -> None:
    assert run("default")["readOnlyApplied"] is True


@needs_node
def test_the_font_size_is_clamped_and_remembered() -> None:
    result = run("default")

    assert result["fontAfterManyIncreases"] == 28
    assert result["storedSize"] == "28"


@needs_node
def test_a_remembered_font_size_is_used_on_the_next_page() -> None:
    assert run("stored-size")["options"]["fontSize"] == 18


@needs_node
def test_blocked_storage_does_not_break_the_editor() -> None:
    result = run("no-storage")

    assert result["options"]["fontSize"] == 14
    assert result["fontAfterManyIncreases"] == 28


@needs_node
def test_an_editor_that_fails_to_load_leaves_a_working_textarea() -> None:
    result = run("loader-fails")

    assert result["options"] is None
    assert result["textareaHidden"] is False
    assert result["classes"] == ["is-plain"]
    assert result["beforeReady"] == STUB


@needs_node
def test_only_the_solution_textarea_becomes_the_workbench_handle() -> None:
    assert run("other-id")["hasHandle"] is False


def test_the_harness_exists() -> None:
    """So a rename cannot turn every test above into a skip."""
    assert HARNESS.is_file()
    assert (static_root() / "editor.js").is_file()
