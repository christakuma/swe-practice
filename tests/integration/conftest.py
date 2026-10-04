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


def a_drill(**overrides: Any) -> dict[str, Any]:
    """A complete, valid SQL drill document."""
    document: dict[str, Any] = {
        "schema_version": 1,
        "id": "sql/one-row-per-customer",
        "kind": "sql_drill",
        "title": "One row per customer",
        "difficulty": "easy",
        "tags": ["joins"],
        "estimated_minutes": 12,
        "prompt": "Return every customer with how many orders they have placed.",
        "hints": ["Which side of the join keeps its rows?"],
        "drill": {
            "seed": "seed.sql",
            "stub": "stub.sql",
            "reference": "solution.sql",
            "checks": [
                {
                    "id": "rows-match",
                    "label": "Every customer appears exactly once",
                    "severity": "required",
                    "assert": "result_matches",
                    "with": {"rows": [["alice", 2], ["bob", 0]]},
                },
            ],
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

    **It appends to `curriculum.yaml` too**, because adding an exercise without
    placing it in the curriculum is a validation failure by design (Phase 11),
    and a harness that did not would make every test here fail for that one
    reason. The manifest is written in *insertion* order, which is what lets
    `test_listing_follows_the_curriculum` write two exercises in reverse id
    order and prove that the manifest rather than the sort decides the listing.

    `curriculum=False` opts out, for the one test whose exercise is deliberately
    in the wrong place on disk and therefore cannot be placed in a track.
    """

    def write(
        document: Mapping[str, Any],
        *,
        directory: str | None = None,
        notes: str | None = "Why revert and not reset.",
        files: Mapping[str, str] | None = None,
        raw: str | None = None,
        curriculum: bool = True,
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
            # Phase 14's three. A drill's seed is real SQL rather than a
            # placeholder comment, because it is the one default here that
            # something *runs*: a seed that will not execute is a
            # `DrillSeedError`, and every drill test would then fail for one
            # uninteresting reason -- which is exactly what this defaulting
            # arrangement exists to prevent.
            "seed.sql": "CREATE TABLE customers (name TEXT);\n",
            "stub.sql": "-- your answer here\n",
            "solution.sql": "SELECT name FROM customers;\n",
        }
        for name, content in {**defaults, **(files or {})}.items():
            if content:
                (path / name).write_text(content, encoding="utf-8")
        if curriculum:
            _place_in_curriculum(library, str(document["id"]))
        return path

    return write


def _place_in_curriculum(library: Path, exercise_id: str) -> None:
    """Append an exercise to the temp library's one-track manifest."""
    manifest = library / "curriculum.yaml"
    listed = []
    if manifest.is_file():
        document = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        listed = list(document["tracks"][0]["exercises"])
    listed.append(exercise_id)
    manifest.write_text(
        yaml.safe_dump(
            {
                "tracks": [
                    {
                        "name": "everything",
                        "title": "Everything in this test library",
                        "exercises": listed,
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
