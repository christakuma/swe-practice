"""Finding the exercises on disk, for every suite that walks the library.

Extracted from `test_fixtures.py` when `test_scenarios.py` needed the same walk.
Two copies of "which directories are git scenarios" would be two chances to
disagree about it, and the way they would disagree is the worst one available: one
suite covering an exercise the other silently skips.

**Discovery is defensive on purpose.** A directory that will not load belongs to no
kind, and crashing collection here would take down every test in both files to
report a problem `test_library.py` already reports precisely. So an unloadable
exercise is left out and `validate` is what names it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.adapters.content import ContentError, load_exercise
from practice.adapters.content.validation import discover
from practice.config import content_root
from practice.domain.exercise import GitScenarioSpec

if TYPE_CHECKING:
    from pathlib import Path

CONTENT_ROOT = content_root()


def identify(directory: Path) -> str:
    """`content/git/revert-a-pushed-commit` -> `git/revert-a-pushed-commit`.

    Which is also the exercise id, an invariant the content suite asserts per
    exercise — so this doubles as the way to look one up in the library.
    """
    return directory.relative_to(CONTENT_ROOT).as_posix()


def scenario_directories() -> list[Path]:
    """Every git scenario directory, in a stable order."""
    found = []
    for directory in sorted(discover(CONTENT_ROOT)):
        try:
            exercise = load_exercise(directory)
        except ContentError:
            continue
        if isinstance(exercise.spec, GitScenarioSpec):
            found.append(directory)
    return found
