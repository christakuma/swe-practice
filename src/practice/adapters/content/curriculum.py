"""The order the library is offered in, declared rather than emergent.

PLAN.md §15 question 4 — *hand-ordered tracks, or prerequisite-graph unlocking?*
— says "start hand-ordered; revisit once there are 50 exercises". There are now
fifty-four, and this is the revisit: still hand-ordered, and now written down
([ADR 0014](../../../../docs/adr/0014-a-hand-ordered-curriculum-manifest.md)).

**What it replaces is an accident.** Until now the library's order was
`sorted(ExerciseId)`, which put `git/amend-the-last-commit` first because `a`
sorts early and `katas/two-sum` last because `t` sorts late. That is not an
ordering anyone chose, and at three exercises nobody noticed; at fifty-four it
is the first thing a solver sees and it is nonsense — `edit-distance` before
`climbing-stairs`, a hard rebase before `amend`.

**Tracks are a manifest, not directories.** An `ExerciseId` is exactly
`<track>/<slug>` and the loader enforces two path segments (PLAN.md §4.1), so
the `git` and `katas` directories are the only two "tracks" the filesystem can
express. The nine pedagogical tracks — history rewriting, recovery and bisect,
arrays and hashing, and so on — are a different and finer grouping, and this
file is where they live. Nothing is moved on disk to express them, which is the
content-as-data bet (§5) holding up under a second kind of structure.

**It is not optional.** `validate_library` requires the manifest to list every
exercise exactly once and to name none that does not exist, so an exercise
added without a line here fails CI rather than quietly appearing at the end. A
manifest that drifts out of date is worse than no manifest: it looks like an
ordering and is a partial one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

import yaml

from practice.adapters.content.errors import ContentError
from practice.domain.errors import InvalidValueError
from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence
    from pathlib import Path

__all__ = [
    "CURRICULUM_FILENAME",
    "Curriculum",
    "Track",
    "curriculum_path",
    "load_curriculum",
    "parse_curriculum",
]

CURRICULUM_FILENAME: Final = "curriculum.yaml"


@dataclass(frozen=True, slots=True)
class Track:
    """One named run of exercises, in the order they are meant to be met."""

    name: str
    title: str
    exercises: tuple[ExerciseId, ...]


@dataclass(frozen=True, slots=True)
class Curriculum:
    """Every track, in order, and the position each exercise sits at.

    `position` is the whole interface. The tracks are kept because they are what
    makes the file readable and what lets a validation failure name the track an
    exercise is missing from — but what the repository needs is one integer per
    exercise, and deriving it once here beats re-scanning the tracks per lookup.
    """

    tracks: tuple[Track, ...]
    _positions: Mapping[ExerciseId, int] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        # Built once, because `position` is called per exercise per listing and
        # re-deriving it from the tracks each time would make an O(n) lookup
        # inside an O(n log n) sort.
        object.__setattr__(
            self,
            "_positions",
            MappingProxyType(
                {
                    exercise_id: index
                    for index, exercise_id in enumerate(self.exercise_ids)
                }
            ),
        )

    @property
    def exercise_ids(self) -> tuple[ExerciseId, ...]:
        """Every id the manifest names, in curriculum order."""
        return tuple(
            exercise_id for track in self.tracks for exercise_id in track.exercises
        )

    def position(self, exercise_id: ExerciseId) -> int:
        """Where this exercise sits, or a position after everything listed.

        An unlisted exercise sorts last rather than raising. `validate_library`
        is what refuses to ship one, and this is the runtime path: someone
        drafting a new exercise should find it at the bottom of the library, not
        find the library refusing to load.
        """
        return self._positions.get(exercise_id, len(self._positions))


def curriculum_path(root: Path) -> Path:
    return root / CURRICULUM_FILENAME


def parse_curriculum(raw: str, *, located_at: Path | str) -> Curriculum:
    """Validate the *text* of a manifest. The disk-free half, for the same reason
    `loader.parse_exercise_file` has one: a pack carries its own manifest as an
    archive entry, and one parser means a packed library and a directory cannot
    disagree about what an ordering is.
    """
    try:
        document: object = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ContentError(located_at, [f"is not valid YAML: {exc}"]) from exc

    problems: list[str] = []
    tracks = tuple(_tracks(document, problems))
    if problems:
        raise ContentError(located_at, problems)
    return Curriculum(tracks=tracks)


def load_curriculum(root: Path) -> Curriculum:
    """Read the manifest, or raise `ContentError` naming what is wrong with it.

    A missing file is an error rather than an empty curriculum. The alternative
    — fall back to the old alphabetical order — is the shape of bug this module
    exists to remove: a tool that silently orders the library by accident when a
    file is renamed.
    """
    path = curriculum_path(root)
    if not path.is_file():
        raise ContentError(path, [f"{CURRICULUM_FILENAME} is missing"])

    return parse_curriculum(path.read_text(encoding="utf-8"), located_at=path)


def _tracks(document: object, problems: list[str]) -> Iterator[Track]:
    """Parse the `tracks:` list, collecting every problem rather than the first.

    Hand-written rather than Pydantic, which is a deliberate inconsistency with
    `schema.py` and worth the sentence: that module models a file with a
    discriminated union, nested blocks and twenty field types, and Pydantic earns
    its keep there. This file is a list of lists of strings. A model would be
    more code than the parsing, and the errors it produced would be located by
    index into a nested structure rather than by track name.
    """
    if not isinstance(document, dict):
        problems.append("must be a mapping with a 'tracks' key")
        return
    raw_tracks = document.get("tracks")
    if not isinstance(raw_tracks, list) or not raw_tracks:
        problems.append("'tracks' must be a non-empty list")
        return

    unknown = sorted(set(document) - {"tracks"})
    if unknown:
        problems.append(f"unknown key(s): {', '.join(unknown)}")

    for index, raw in enumerate(raw_tracks):
        track = _track(raw, index, problems)
        if track is not None:
            yield track


def _track(raw: object, index: int, problems: list[str]) -> Track | None:
    where = f"tracks[{index}]"
    if not isinstance(raw, dict):
        problems.append(f"{where}: must be a mapping")
        return None

    name = raw.get("name")
    title = raw.get("title")
    listed = raw.get("exercises")
    if not isinstance(name, str) or not name.strip():
        problems.append(f"{where}: needs a name")
        return None
    if not isinstance(title, str) or not title.strip():
        problems.append(f"{where} ({name}): needs a title")
        return None
    if not isinstance(listed, list) or not listed:
        problems.append(f"{where} ({name}): needs a non-empty 'exercises' list")
        return None

    exercises = tuple(_exercise_ids(listed, name, problems))
    if not exercises:
        return None
    return Track(name=name, title=title, exercises=exercises)


def _exercise_ids(
    listed: Sequence[object], track: str, problems: list[str]
) -> Iterator[ExerciseId]:
    """Validate each id through `ExerciseId`, so one type decides what one is.

    The same reason `schema.py` builds domain value objects inside its
    validators: the rule that an id is exactly `<track>/<slug>` lives in the
    domain, and restating it here as a regular expression would be a second
    place for it to be wrong.
    """
    for raw in listed:
        if not isinstance(raw, str):
            problems.append(f"{track}: {raw!r} is not an exercise id")
            continue
        try:
            yield ExerciseId(raw)
        except InvalidValueError as exc:
            problems.append(f"{track}: {raw!r} {exc}")
