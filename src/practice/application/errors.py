"""What a use case raises when it cannot do the thing it was asked to do.

Separate from `domain/errors.py` because the two have different causes and
different readers. A `DomainError` means an aggregate refused an operation — a
rule of the model was broken. These mean the *request* could not be satisfied:
nothing resolves that id, nothing can grade that kind of exercise, the workspace
is gone. The domain knows nothing about any of those, because each one is a
question about something behind a port.

Kept as four narrow types rather than one error with a code, because every
driving adapter has to map them to something — an exit status in the CLI, a
status code in the web app — and a match on a type is checked by mypy while a
match on a string is not.
"""

from __future__ import annotations

__all__ = [
    "ApplicationError",
    "AttemptNotFoundError",
    "ExerciseNotFoundError",
    "UnsupportedExerciseKindError",
    "WorkspaceGoneError",
]


class ApplicationError(Exception):
    """Base class for every error raised from `practice.application`."""


class ExerciseNotFoundError(ApplicationError):
    """No exercise in the library has that id."""


class AttemptNotFoundError(ApplicationError):
    """No stored attempt has that id.

    Expected rather than exceptional now that attempts outlive a process: a
    mistyped id, a link from a browser tab left open across a reinstall, an id from
    a database that has since been deleted. Every one of those is a normal thing
    for a caller to turn into a message.
    """


class WorkspaceGoneError(ApplicationError):
    """The attempt is still active but its workspace is no longer on disk.

    The failure `practice gc` will be able to cause on purpose, so it is worth a
    type of its own: the attempt can be *abandoned* but never *graded*, and the
    distinction is the whole reason PLAN.md §8.1 ties workspace lifetime to the
    `ACTIVE` status.
    """


class UnsupportedExerciseKindError(ApplicationError):
    """Nothing registered can grade an exercise of that kind.

    A real condition during the MVP rather than a defensive branch: `git_scenario`
    has no grader until Phase 5, and an honest refusal naming the phase is much
    better than provisioning a workspace, running a fixture and then discovering
    there is nothing to grade it with.
    """
