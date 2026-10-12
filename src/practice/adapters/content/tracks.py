"""`tracks.yaml`: the routes through the library somebody can follow.

The second manifest, beside `curriculum.yaml` and deliberately not inside it
([ADR 0025](../../../../docs/adr/0025-tracks-are-a-second-manifest.md)). The
curriculum is one order over everything, each exercise named exactly once; a
track is a named selection with an order of its own, and the same exercise can
be on several. Two files because they hold two different promises, and
`validate_library` checks each one's separately.

**Two spellings of a track, and only one of them lists anything.**

    - name: blind-75
      exercises: [katas/two-sum, katas/contains-a-duplicate, ...]

    - name: everything
      follows: curriculum

`follows: curriculum` is *every exercise, in the curriculum's order*, and it
exists so that the whole-library track is not a hundred and fifteen lines
restating the file next door — a copy that would be wrong the first time
somebody added an exercise to one and not the other. An explicit list is for a
track that selects, or reorders, or both.

**A declaration is not a track.** `TrackDeclaration` is what the file says and
`practice.domain.track.Track` is what it means once `resolve` has turned
`follows` into ids. The split is what lets a pack carry the file narrowed to its
own exercises without knowing what the curriculum was, and what lets
`validate_library` complain about the text of a list that `resolve` would
quietly tolerate.

**The file is optional, and the curriculum is not; the asymmetry is on
purpose.** A library with no `curriculum.yaml` has no order, and falling back to
an alphabetical one restores the accident that manifest was written to remove.
A library with no `tracks.yaml` has simply not offered any tracks: the page says
so, nothing is silently reordered, and every library and pack written before
this file existed keeps loading.

**Lenient at runtime, strict in `validate`, like the curriculum.** `resolve`
drops an id the library does not hold rather than raising, so somebody halfway
through renaming an exercise finds a track one step short instead of a server
that will not start. `validate_library` is what refuses to ship it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import yaml

from practice.adapters.content.errors import ContentError
from practice.domain.errors import InvalidValueError
from practice.domain.ids import ExerciseId
from practice.domain.track import Track

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from pathlib import Path

__all__ = [
    "FOLLOWS_CURRICULUM",
    "TRACKS_FILENAME",
    "TrackDeclaration",
    "load_tracks",
    "narrow_tracks",
    "parse_tracks",
    "render_tracks",
    "resolve_tracks",
    "tracks_path",
]

TRACKS_FILENAME: Final = "tracks.yaml"

#: The one thing `follows:` can name. A string rather than a boolean so the line
#: reads as what it means, and so a second thing to follow would be a second
#: value rather than a second key.
FOLLOWS_CURRICULUM: Final = "curriculum"

_KEYS: Final = frozenset({"name", "title", "summary", "exercises", "follows"})

#: Stands in for the steps of a track that follows the curriculum while its
#: name is being validated; see `_declaration`. Never stored and never listed.
_PROBE_STEP: Final = ExerciseId("probe/step")


@dataclass(frozen=True, slots=True)
class TrackDeclaration:
    """One entry of `tracks.yaml`, as written.

    `exercises` is `None` for a track that follows the curriculum, which is the
    only other thing a track can do — so one optional field carries the whole
    choice and there is no state in which both spellings are set.
    """

    name: str
    title: str
    summary: str
    exercises: tuple[ExerciseId, ...] | None = None

    @property
    def follows_curriculum(self) -> bool:
        return self.exercises is None


def tracks_path(root: Path) -> Path:
    return root / TRACKS_FILENAME


def load_tracks(root: Path) -> tuple[TrackDeclaration, ...]:
    """Read the manifest, or `()` when the library has none.

    See the module docstring for why a missing file is not the error a missing
    `curriculum.yaml` is. A file that is *present and wrong* still raises
    `ContentError`: declining to offer tracks is a choice, and a typo is not.
    """
    path = tracks_path(root)
    if not path.is_file():
        return ()
    return parse_tracks(path.read_text(encoding="utf-8"), located_at=path)


def parse_tracks(raw: str, *, located_at: Path | str) -> tuple[TrackDeclaration, ...]:
    """Validate the *text* of a manifest. Disk-free for the reason
    `parse_curriculum` is: a pack carries its own copy as an archive entry, and
    one parser means a packed library and a directory cannot disagree about what
    a track is.

    Collects every problem rather than stopping at the first, and refuses the
    two things `Track` itself would refuse — a repeated name and a repeated
    step — here, where the complaint can name the file.
    """
    try:
        document: object = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ContentError(located_at, [f"is not valid YAML: {exc}"]) from exc

    problems: list[str] = []
    declarations = tuple(_declarations(document, problems))

    names = [declaration.name for declaration in declarations]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        problems.append(f"declares twice: {', '.join(repeated)}")

    if problems:
        raise ContentError(located_at, problems)
    return declarations


def resolve_tracks(
    declarations: Iterable[TrackDeclaration], library: Sequence[ExerciseId]
) -> tuple[Track, ...]:
    """Declarations into tracks, against the exercises a library actually holds.

    `library` is every exercise id **in curriculum order**, which is the one
    thing both spellings need: `follows: curriculum` becomes exactly that
    sequence, and an explicit list is filtered to what is in it.

    A track left with nothing on it is dropped rather than built, because
    `Track` refuses to be empty and a track nobody can take a step on is not
    worth a row on a page.
    """
    held = frozenset(library)
    tracks = []
    for declaration in declarations:
        listed = (
            tuple(library)
            if declaration.exercises is None
            else tuple(found for found in declaration.exercises if found in held)
        )
        if listed:
            tracks.append(
                Track(
                    name=declaration.name,
                    title=declaration.title,
                    summary=declaration.summary,
                    exercises=listed,
                )
            )
    return tuple(tracks)


def narrow_tracks(
    declarations: Iterable[TrackDeclaration], selected: Iterable[ExerciseId]
) -> tuple[TrackDeclaration, ...]:
    """The same declarations with everything unselected removed. For a pack.

    The counterpart of `pack._narrowed`, and for its reason: a pack of part of a
    library that copied the whole file would install to a content root
    `practice validate` refuses, naming exercises that are not there. A track
    that follows the curriculum needs no narrowing — the pack's own curriculum
    is already the narrowed one — and an explicit track left holding nothing is
    dropped, because the parser that reads the pack back refuses an empty list.
    """
    keep = frozenset(selected)
    narrowed = []
    for declaration in declarations:
        if declaration.exercises is None:
            narrowed.append(declaration)
            continue
        kept = tuple(found for found in declaration.exercises if found in keep)
        if kept:
            narrowed.append(
                TrackDeclaration(
                    name=declaration.name,
                    title=declaration.title,
                    summary=declaration.summary,
                    exercises=kept,
                )
            )
    return tuple(narrowed)


def render_tracks(declarations: Iterable[TrackDeclaration], *, header: str) -> bytes:
    """Declarations back into the YAML `parse_tracks` reads. For a pack.

    `sort_keys=False` so a track reads name, title, summary, then its steps —
    the order of the steps is the data, and the order of the keys is what makes
    the file legible to the person who opens it.
    """
    document = {
        "tracks": [
            {
                "name": declaration.name,
                "title": declaration.title,
                "summary": declaration.summary,
                **(
                    {"follows": FOLLOWS_CURRICULUM}
                    if declaration.exercises is None
                    else {
                        "exercises": [
                            exercise_id.value for exercise_id in declaration.exercises
                        ]
                    }
                ),
            }
            for declaration in declarations
        ]
    }
    body = yaml.safe_dump(
        document, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    return (header + body).encode("utf-8")


# --- parsing ---------------------------------------------------------------


def _declarations(document: object, problems: list[str]) -> Iterator[TrackDeclaration]:
    """Hand-written rather than Pydantic, for the reason `curriculum._tracks`
    gives: this is a list of small mappings, a model would be more code than the
    parsing, and its errors would be located by index rather than by the name a
    reader would search the file for.
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
        declaration = _declaration(raw, index, problems)
        if declaration is not None:
            yield declaration


def _declaration(
    raw: object, index: int, problems: list[str]
) -> TrackDeclaration | None:
    where = f"tracks[{index}]"
    if not isinstance(raw, dict):
        problems.append(f"{where}: must be a mapping")
        return None

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        problems.append(f"{where}: needs a name")
        return None

    before = len(problems)
    unknown = sorted(str(key) for key in set(raw) - _KEYS)
    if unknown:
        problems.append(f"{name}: unknown key(s): {', '.join(unknown)}")

    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        problems.append(f"{name}: needs a title")
    summary = raw.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        # Required, unlike a curriculum section's nothing-at-all: a track is
        # something a person chooses, and a title alone does not say whether
        # the Blind 75 here is the list they know or somebody's variation.
        problems.append(f"{name}: needs a summary saying what the track is for")

    exercises = _steps(raw, name, problems)
    if len(problems) > before:
        return None

    declaration = TrackDeclaration(
        name=name,
        title=str(title).strip(),
        summary=str(summary).strip(),
        exercises=exercises,
    )
    try:
        # Built and thrown away, so that the two rules this module does not
        # restate -- what a track's name may look like, and that no step
        # repeats -- stay the domain's to decide and are still reported against
        # the file rather than at first use. A track that follows the
        # curriculum has no list to check yet, so it is probed with one step.
        Track(
            name=declaration.name,
            title=declaration.title,
            summary=declaration.summary,
            exercises=exercises if exercises is not None else (_PROBE_STEP,),
        )
    except InvalidValueError as exc:
        problems.append(str(exc))
        return None
    return declaration


def _steps(
    raw: dict[object, object], name: str, problems: list[str]
) -> tuple[ExerciseId, ...] | None:
    """The track's own list, or `None` for one that follows the curriculum.

    Exactly one of the two spellings. Both would leave a reader guessing which
    won, and neither is a track with nothing on it.
    """
    follows = raw.get("follows")
    listed = raw.get("exercises")
    if (follows is None) == (listed is None):
        problems.append(
            f"{name}: needs exactly one of 'exercises' (a list of ids) or "
            f"'follows: {FOLLOWS_CURRICULUM}'"
        )
        return None
    if listed is None:
        if follows != FOLLOWS_CURRICULUM:
            problems.append(
                f"{name}: 'follows' can only name '{FOLLOWS_CURRICULUM}', "
                f"got {follows!r}"
            )
        return None

    if not isinstance(listed, list) or not listed:
        problems.append(f"{name}: 'exercises' must be a non-empty list")
        return None
    return tuple(_exercise_ids(listed, name, problems))


def _exercise_ids(
    listed: Sequence[object], track: str, problems: list[str]
) -> Iterator[ExerciseId]:
    """Each id through `ExerciseId`, so one type decides what an id is."""
    for raw in listed:
        if not isinstance(raw, str):
            problems.append(f"{track}: {raw!r} is not an exercise id")
            continue
        try:
            yield ExerciseId(raw)
        except InvalidValueError as exc:
            problems.append(f"{track}: {raw!r} {exc}")
