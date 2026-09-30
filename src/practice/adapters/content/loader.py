"""One exercise directory becomes one `Exercise`.

Loading and auditing are separate jobs and live in separate modules. This one
answers "can this directory be read as an exercise?"; `validation` answers "is
it a good one, and do the files it names exist?". The split matters because the
web app and the CLI want different answers: browsing the library should not fail
because an exercise someone is drafting has an empty `notes.md`, while
`practice validate` must say so.

**The id must match the directory.** `ExerciseId` is exactly two segments
because the id *is* the content path (PLAN.md §4.1). A file whose `id:` says
something else is the disagreement that rule exists to prevent, so it is refused
here rather than resolved in favour of one or the other.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

import yaml
from pydantic import ValidationError

from practice.adapters.content.errors import ContentError
from practice.adapters.content.schema import EXERCISE_FILE
from practice.domain.exercise import ExerciseKind
from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from pathlib import Path

    from practice.adapters.content.schema import ExerciseFile
    from practice.domain.exercise import Exercise

__all__ = [
    "EXERCISE_FILENAME",
    "NOTES_FILENAME",
    "exercise_id_for",
    "load_exercise",
    "load_exercise_file",
    "read_notes",
]

EXERCISE_FILENAME: Final = "exercise.yaml"
NOTES_FILENAME: Final = "notes.md"

#: The tags Pydantic prefixes to every location when it validates through a
#: discriminated union. They say which arm was tried, which is noise once the
#: arm was chosen correctly — and it always was, because the tag is `kind`.
_DISCRIMINATOR_TAGS: Final = frozenset(str(kind) for kind in ExerciseKind)


def exercise_id_for(directory: Path) -> ExerciseId:
    """The id a directory implies: `<track>/<slug>` from its last two segments."""
    return ExerciseId(f"{directory.parent.name}/{directory.name}")


def read_notes(directory: Path) -> str:
    """`notes.md`, or empty if there is none.

    Missing notes are not a load failure. "Notes are non-empty" is a rule about a
    *good* exercise rather than a *representable* one, and the same line that
    keeps it out of the domain keeps it out of here — it belongs to
    `validation`, which is allowed to have opinions (PLAN.md §4.2, §9).
    """
    notes = directory / NOTES_FILENAME
    return notes.read_text(encoding="utf-8") if notes.is_file() else ""


def load_exercise_file(path: Path) -> ExerciseFile:
    """Parse and validate one `exercise.yaml`.

    Raises `ContentError` carrying every problem the file has, each located.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContentError(path, [f"cannot be read: {exc.strerror or exc}"]) from exc

    try:
        document: Any = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ContentError(path, [_describe_yaml_error(exc)]) from exc

    if document is None:
        raise ContentError(path, ["is empty"])
    if not isinstance(document, dict):
        raise ContentError(
            path, [f"must be a mapping of keys, not a {type(document).__name__}"]
        )

    try:
        return EXERCISE_FILE.validate_python(document)
    except ValidationError as exc:
        raise ContentError(path, _describe(exc)) from exc


def load_exercise(directory: Path) -> Exercise:
    """Read one exercise directory: the YAML, plus `notes.md` alongside it."""
    path = directory / EXERCISE_FILENAME
    if not path.is_file():
        raise ContentError(path, ["no such file"])

    parsed = load_exercise_file(path)
    expected = exercise_id_for(directory)
    if parsed.id != expected.value:
        raise ContentError(
            path,
            [
                (
                    f"id: {parsed.id!r} does not match the directory it is in; "
                    f"expected {expected.value!r}"
                )
            ],
        )
    return parsed.to_exercise(notes=read_notes(directory))


# --- turning a ValidationError into something an author can act on ---------


def _describe(error: ValidationError) -> tuple[str, ...]:
    """`scenario.checks.0.assert: unknown assertion 'tree_equal'`, one per line.

    Pydantic's own rendering is complete and unreadable — it repeats the model
    name, the input value and a docs URL for each of what may be a dozen errors.
    What an author needs is the path and the sentence.
    """
    problems = []
    for item in error.errors():
        location = [str(part) for part in item["loc"]]
        if location and location[0] in _DISCRIMINATOR_TAGS:
            location.pop(0)
        # Pydantic prefixes anything raised as a `ValueError` — which is every
        # domain invariant reaching this layer — with "Value error, ".
        message = item["msg"].removeprefix("Value error, ")
        problems.append(f"{'.'.join(location)}: {message}" if location else message)
    return tuple(sorted(problems))


def _describe_yaml_error(error: yaml.YAMLError) -> str:
    """Keep the line and column PyYAML found, and drop the rest.

    A syntax error without a position is the one case where the reader has to
    go hunting, so this is worth unpacking rather than stringifying.
    """
    mark = getattr(error, "problem_mark", None)
    problem = getattr(error, "problem", None) or "is not valid YAML"
    if mark is None:
        return f"is not valid YAML: {problem}"
    return f"line {mark.line + 1}, column {mark.column + 1}: {problem}"
