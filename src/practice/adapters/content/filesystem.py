"""`ContentRepository` over a directory of exercises.

**A broken exercise fails the whole listing.** The tempting alternative is to
skip anything that will not load, so the library still browses. That is how an
exercise disappears without anyone noticing it has gone — the tool looks healthy
and is quietly one exercise smaller. `practice validate` exists so this never
has to be discovered at runtime, and it runs in CI for the same reason.

**Loaded once, then cached.** Content is read-only at runtime and there are
tens of exercises, not thousands, so the simple thing is the right thing.
Phase 10's "solve it in my own editor" mode watches the *workspace*, not the
content root; if content reload ever becomes a feature it gets an explicit
method rather than a stat on every call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.adapters.content.curriculum import load_curriculum
from practice.adapters.content.loader import load_exercise
from practice.adapters.content.validation import discover

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from practice.adapters.content.curriculum import Curriculum
    from practice.domain.exercise import Exercise, ExerciseFilter
    from practice.domain.ids import ExerciseId

__all__ = ["FilesystemContentRepository"]


class FilesystemContentRepository:
    """Satisfies `practice.domain.ports.ContentRepository`.

    Structurally, not by inheritance — the port is a `Protocol`, so this class
    does not import it and the dependency arrow keeps pointing inward (ADR 0002).
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._exercises: dict[ExerciseId, Exercise] | None = None
        self._order: Curriculum | None = None

    @property
    def root(self) -> Path:
        return self._root

    def list_exercises(
        self, criteria: ExerciseFilter | None = None
    ) -> Sequence[Exercise]:
        """Every exercise the filter accepts, in curriculum order.

        **Ordered by `content/curriculum.yaml` since Phase 11**, where it used to
        be ordered by id — which meant alphabetically, which meant `amend` first
        because `a` sorts early and `edit-distance` before `climbing-stairs`. At
        three exercises nobody noticed; at fifty-four it is the first thing a
        solver sees. Every caller that offers the library to a human inherits
        this: the browse page, and the unscheduled half of the review queue.

        The matching is `ExerciseFilter.matches`, which lives in the domain so
        that this repository and any in-memory fake cannot disagree about what a
        filter means — the drift that stops a fake being evidence of anything.
        """
        exercises = self._loaded()
        if not exercises:
            # Whether an empty library is a problem is `practice validate`'s
            # call, and a manifest for nothing is not required to exist.
            return []
        order = self._curriculum().position
        ordered = sorted(exercises.values(), key=lambda found: order(found.id))
        if criteria is None:
            return ordered
        return [exercise for exercise in ordered if criteria.matches(exercise)]

    def get(self, exercise_id: ExerciseId) -> Exercise | None:
        """The exercise, or `None` if the library does not have it.

        `None` rather than an exception because "no such exercise" is a 404 on a
        URL someone bookmarked, not a fault.
        """
        return self._loaded().get(exercise_id)

    def _curriculum(self) -> Curriculum:
        """The manifest, read once. Cached for the same reason the exercises are.

        A missing or malformed manifest raises `ContentError`, which fails the
        listing — the same choice as a broken exercise, and for the same reason
        given at the top of this module. Falling back to alphabetical order would
        restore the accident this replaced, silently.
        """
        if self._order is None:
            self._order = load_curriculum(self._root)
        return self._order

    def _loaded(self) -> dict[ExerciseId, Exercise]:
        if self._exercises is None:
            self._exercises = {
                exercise.id: exercise
                for exercise in (
                    load_exercise(directory) for directory in discover(self._root)
                )
            }
        return self._exercises
