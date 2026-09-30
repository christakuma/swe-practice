"""A content library built in a temp directory, one exercise at a time.

Real files rather than a mocked filesystem, which is why these are integration
tests: everything interesting here is about what is and is not on disk — a
missing `notes.md`, a `solution.cmds` that names a command the exercise does not
allow, an exercise nested a level too deep. A fake filesystem would let every
one of those pass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

SOLUTION = """\
# Reference solution.
git log --oneline
git revert --no-edit HEAD
git push origin main
"""

NAIVE = """\
# The tempting wrong answer.
git reset --hard HEAD~1
git push --force origin main
"""


def a_scenario(**overrides: Any) -> dict[str, Any]:
    """A complete, valid git scenario document."""
    document: dict[str, Any] = {
        "schema_version": 1,
        "id": "git/undo-a-commit",
        "kind": "git_scenario",
        "title": "Undo a commit",
        "difficulty": "medium",
        "tags": ["history"],
        "estimated_minutes": 10,
        "prompt": "Undo the last commit without rewriting published history.",
        "hints": ["What does your teammate already have?"],
        "scenario": {
            "fixture": "fixture.sh",
            "reference": "solution.cmds",
            "counter_examples": [
                {"file": "naive.cmds", "expect_failures": ["history-preserved"]}
            ],
            "allowed_commands": ["git", "cat"],
            "checks": [
                {
                    "id": "history-preserved",
                    "label": "The bad commit is still reachable",
                    "severity": "required",
                    "assert": "is_ancestor",
                    "with": {"ancestor": "@c3", "descendant": "HEAD"},
                }
            ],
        },
    }
    document.update(overrides)
    return document


def a_kata(**overrides: Any) -> dict[str, Any]:
    """A complete, valid kata document."""
    document: dict[str, Any] = {
        "schema_version": 1,
        "id": "katas/two-sum",
        "kind": "kata",
        "title": "Two Sum",
        "difficulty": "easy",
        "tags": ["arrays"],
        "estimated_minutes": 15,
        "prompt": "Return the indices of the two numbers that sum to the target.",
        "hints": ["Trade space for time."],
        "kata": {
            "language": "python",
            "stub": "stub.py",
            "tests": "tests.py",
            "reference": "solution.py",
        },
    }
    document.update(overrides)
    return document


type WriteExercise = Callable[..., Path]


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """An empty content root."""
    root = tmp_path / "content"
    root.mkdir()
    return root


@pytest.fixture
def write_exercise(library: Path) -> WriteExercise:
    """Write one exercise directory, defaulting every sibling file it names.

    Defaulting them is what keeps the failure tests honest: a test about a
    missing `notes.md` has to be the *only* thing wrong with that exercise, or
    it proves nothing about which problem was detected.
    """

    def write(
        document: Mapping[str, Any],
        *,
        directory: str | None = None,
        notes: str | None = "Why revert and not reset.",
        files: Mapping[str, str] | None = None,
        raw: str | None = None,
    ) -> Path:
        path = library / (directory if directory is not None else str(document["id"]))
        path.mkdir(parents=True, exist_ok=True)
        (path / "exercise.yaml").write_text(
            raw if raw is not None else yaml.safe_dump(dict(document), sort_keys=False),
            encoding="utf-8",
        )
        if notes is not None:
            (path / "notes.md").write_text(notes, encoding="utf-8")

        defaults = {
            "fixture.sh": "#!/usr/bin/env bash\n",
            "solution.cmds": SOLUTION,
            "naive.cmds": NAIVE,
            "stub.py": "def two_sum(): ...\n",
            "tests.py": "def test_it(): ...\n",
            "solution.py": "def two_sum(): ...\n",
        }
        for name, content in {**defaults, **(files or {})}.items():
            if content:
                (path / name).write_text(content, encoding="utf-8")
        return path

    return write
