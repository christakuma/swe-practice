"""`practice context`: an attempt, printed for somebody else to read.

Integration tests for the reason the lifecycle ones are: every case here starts
a real attempt in a real workspace and reads it back from a real database in a
*separate* invocation, which is the only way to show the bundle is built from
what was stored rather than from what one process happened to be holding.

What they are mostly about is the two things a unit test of the renderer cannot
see -- that the command's stdout is the bundle and nothing else, because it is
piped, and that the exercise's own answers do not reach it while the attempt is
open, against a real exercise rather than a fake one.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from practice.application.tutor import TUTOR_PROMPT
from practice.interface.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

TWO_SUM = "katas/two-sum"
REVERT = "git/revert-a-pushed-commit"

runner = CliRunner()


@pytest.fixture
def storage(tmp_path: Path) -> tuple[Path, Path]:
    """A disposable workspace root and database, as every invocation gets."""
    return tmp_path / "ws", tmp_path / "practice.db"


def run(storage: tuple[Path, Path], *arguments: str) -> tuple[int, str, str]:
    """One command against both paths. Stdout and stderr come back apart,
    because which of the two a line went to is half of what is tested here.
    """
    workspaces, database = storage
    result = runner.invoke(
        app,
        [
            *arguments,
            "--workspace-root",
            str(workspaces),
            "--database",
            str(database),
        ],
    )
    return result.exit_code, result.stdout, result.stderr


def start(storage: tuple[Path, Path], exercise: str, *flags: str) -> str:
    code, output, _ = run(storage, "start", exercise, "--no-prompt", *flags)
    assert code == 0, output
    for line in output.splitlines():
        if "attempt " in line:
            return line.split("attempt ", 1)[1].strip()
    raise AssertionError(f"no attempt id in:\n{output}")


def replay(storage: tuple[Path, Path], attempt_id: str, *lines: str) -> None:
    commands = storage[0].parent / "more.cmds"
    commands.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    code, output, _ = run(storage, "resume", attempt_id, "--commands", str(commands))
    assert code == 0, output


# --- what it prints --------------------------------------------------------


def test_it_prints_the_prompt_the_task_and_what_was_run(
    storage: tuple[Path, Path],
) -> None:
    attempt_id = start(storage, REVERT)
    replay(storage, attempt_id, "git log --oneline")

    code, out, err = run(storage, "context", attempt_id)

    assert code == 0, err
    assert out.startswith(TUTOR_PROMPT)
    assert "# Undo a commit that is already on origin" in out
    assert "**1.** Ran `git log --oneline` (exit 0)" in out
    # Read from the live repository in this invocation, not replayed from the
    # log: the fixture's three commits, with HEAD on the published branch.
    assert "- HEAD: `main` at `" in out
    assert "(HEAD, main, origin/main)" in out
    assert err == ""


def test_stdout_is_the_bundle_and_nothing_else(storage: tuple[Path, Path]) -> None:
    """It is piped to a clipboard, so a status line on stdout would be pasted
    into a chat as though it were part of the attempt.
    """
    attempt_id = start(storage, REVERT)

    _, out, _ = run(storage, "context", attempt_id)

    assert out.endswith("[parents: none]\n")
    assert "  ok   " not in out


def test_an_open_attempt_gives_none_of_the_exercises_answers_away(
    storage: tuple[Path, Path],
) -> None:
    """Against the real exercise: its last hint names the command, its notes
    explain the lesson, and its checks name the end state.
    """
    attempt_id = start(storage, REVERT)

    _, out, _ = run(storage, "context", attempt_id)

    assert "not yet revealed" in out
    assert "git revert" not in out
    assert "## The verdict" not in out
    assert "## The author's notes" not in out


def test_a_graded_attempt_becomes_a_post_mortem(storage: tuple[Path, Path]) -> None:
    attempt_id = start(storage, REVERT)
    code, output, _ = run(storage, "submit", attempt_id)
    assert code == 1, output  # nothing was fixed, so it fails; that is the point
    assert "still open" in output
    # Still open after a failure (ADR 0029), so it is conceded to finish it.
    code, output, _ = run(storage, "concede", attempt_id)
    assert code == 1, output
    assert "conceded after 1 failed submission" in output

    code, out, err = run(storage, "context", attempt_id)

    assert code == 0, err
    assert "- Attempt: completed, practice mode" in out
    assert "## The verdict\n\nOutcome: fail" in out
    assert "## The author's notes" in out
    assert "no longer on disk" in out


def test_a_katas_bundle_carries_the_file_in_the_workspace(
    storage: tuple[Path, Path],
) -> None:
    attempt_id = start(storage, TWO_SUM)

    code, out, err = run(storage, "context", attempt_id)

    assert code == 0, err
    assert "## My solution as it stands\n\n```python\n" in out
    assert "def two_sum" in out
    # The hidden suite is in the same directory, and stays there.
    assert "def test_" not in out
    assert "The repository" not in out


def test_source_overrides_the_file_in_the_workspace(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    attempt_id = start(storage, TWO_SUM)
    mine = tmp_path / "mine.py"
    mine.write_text("def two_sum(numbers, target):\n    return (0, 1)\n", "utf-8")

    _, out, _ = run(storage, "context", attempt_id, "--source", str(mine))

    assert "    return (0, 1)" in out


# --- the other format, and the file ----------------------------------------


def test_json_is_the_same_attempt_as_data(storage: tuple[Path, Path]) -> None:
    attempt_id = start(storage, REVERT)
    replay(storage, attempt_id, "git status")

    code, out, err = run(storage, "context", attempt_id, "--format", "json")

    assert code == 0, err
    data = json.loads(out)
    assert data["tutor_prompt"] == TUTOR_PROMPT
    assert data["exercise"]["id"] == REVERT
    assert [event["command"] for event in data["events"]] == ["git status"]
    assert data["repository"]["head"]["branch"] == "main"
    assert data["verdict"] is None
    assert data["notes"] is None


def test_output_writes_utf8_with_lf_endings_and_keeps_stdout_empty(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    """The path that survives a Windows pipeline: the same bytes, with nothing
    in between to re-decode them.
    """
    attempt_id = start(storage, REVERT)
    target = tmp_path / "bundle.md"

    code, out, err = run(storage, "context", attempt_id, "--output", str(target))

    assert code == 0, err
    assert out == ""
    assert "wrote" in err
    written = target.read_bytes()
    assert written.decode("utf-8").startswith(TUTOR_PROMPT)
    assert b"\r\n" not in written


def test_piped_output_is_utf8_whatever_the_console_is(
    storage: tuple[Path, Path],
) -> None:
    """Run under a cp1252 stdout, which is what a pipe is on a Windows machine
    nobody has configured. This exercise's task holds an em dash, so the bytes
    are only valid UTF-8 if the command wrote them itself rather than leaving
    the encoding to the stream -- and written through the stream they would be
    a lone 0x97, which does not decode.
    """
    attempt_id = start(storage, REVERT)

    result = CliRunner(charset="cp1252").invoke(
        app,
        [
            "context",
            attempt_id,
            "--workspace-root",
            str(storage[0]),
            "--database",
            str(storage[1]),
        ],
    )

    assert result.exit_code == 0, result.stderr
    text = result.stdout_bytes.decode("utf-8")
    assert "working again \N{EM DASH} on your machine" in text
    assert b"\r\n" not in result.stdout_bytes


# --- what it refuses -------------------------------------------------------


def test_an_open_interview_is_refused_on_stderr(storage: tuple[Path, Path]) -> None:
    """On stderr, so the refusal is read by the person and not pasted to the
    model -- and with nothing on stdout for a pipe to carry.
    """
    attempt_id = start(storage, REVERT, "--interview")

    code, out, err = run(storage, "context", attempt_id)

    assert code == 2
    assert out == ""
    assert "interview mode withholds the tutor" in err


def test_an_unknown_attempt_is_refused_on_stderr(storage: tuple[Path, Path]) -> None:
    code, out, err = run(storage, "context", "00000000-0000-4000-8000-000000000000")

    assert code == 2
    assert out == ""
    assert "no attempt with id" in err
