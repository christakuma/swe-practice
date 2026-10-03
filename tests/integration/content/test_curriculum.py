"""`curriculum.yaml` — the manifest that decides what order the library is in.

An integration test rather than a unit one because the loader reads a file: it
is here beside `test_validation.py` for the same reason that one is, and the
`library` fixture writes real YAML to a real temp directory.

What is tested is the refusals. The happy path is covered by the content suite
over the shipped manifest (`tests/content/test_library.py`), which is a stronger
statement than any fixture here — fifty-four exercises in a hand-written order —
and what this file adds is every way an author can get the file wrong.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from practice.adapters.content import ContentError
from practice.adapters.content.curriculum import load_curriculum
from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def write(library: Path, document: object) -> Path:
    (library / "curriculum.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )
    return library


def a_manifest(**overrides: object) -> Mapping[str, object]:
    track: dict[str, object] = {
        "name": "git-foundations",
        "title": "Git: the operations you undo things with",
        "exercises": ["git/amend-the-last-commit", "katas/two-sum"],
    }
    track.update(overrides)
    return {"tracks": [track]}


def problems(library: Path) -> tuple[str, ...]:
    with pytest.raises(ContentError) as caught:
        load_curriculum(library)
    return caught.value.problems


# --- the happy path --------------------------------------------------------


def test_it_reads_tracks_in_order(library: Path) -> None:
    write(
        library,
        {
            "tracks": [
                {"name": "a", "title": "First", "exercises": ["git/one"]},
                {"name": "b", "title": "Second", "exercises": ["katas/two"]},
            ]
        },
    )

    curriculum = load_curriculum(library)

    assert [track.name for track in curriculum.tracks] == ["a", "b"]
    assert curriculum.exercise_ids == (ExerciseId("git/one"), ExerciseId("katas/two"))


def test_position_follows_the_order_across_tracks(library: Path) -> None:
    """Positions are over the whole manifest, not per track — otherwise the
    second track's first exercise would tie with the first track's.
    """
    write(
        library,
        {
            "tracks": [
                {"name": "a", "title": "First", "exercises": ["git/one", "git/two"]},
                {"name": "b", "title": "Second", "exercises": ["katas/three"]},
            ]
        },
    )

    curriculum = load_curriculum(library)

    assert curriculum.position(ExerciseId("git/one")) == 0
    assert curriculum.position(ExerciseId("git/two")) == 1
    assert curriculum.position(ExerciseId("katas/three")) == 2


def test_an_unlisted_exercise_sorts_last_rather_than_raising(library: Path) -> None:
    """The runtime path for an exercise someone is drafting. `validate_library`
    is what refuses to ship one; the repository should still list it.
    """
    write(library, a_manifest())

    curriculum = load_curriculum(library)

    assert curriculum.position(ExerciseId("katas/brand-new")) == 2


# --- the refusals ----------------------------------------------------------


def test_a_missing_manifest_is_an_error_not_an_empty_curriculum(
    library: Path,
) -> None:
    """Falling back to alphabetical order would restore the accident the
    manifest replaced, silently, the first time the file was renamed.
    """
    assert problems(library) == ("curriculum.yaml is missing",)


def test_yaml_that_will_not_parse_says_so(library: Path) -> None:
    (library / "curriculum.yaml").write_text("tracks: [unclosed", encoding="utf-8")

    assert "is not valid YAML" in problems(library)[0]


def test_a_document_that_is_not_a_mapping_is_refused(library: Path) -> None:
    write(library, ["git/one"])

    assert problems(library) == ("must be a mapping with a 'tracks' key",)


def test_an_empty_track_list_is_refused(library: Path) -> None:
    write(library, {"tracks": []})

    assert problems(library) == ("'tracks' must be a non-empty list",)


def test_an_unknown_top_level_key_is_refused(library: Path) -> None:
    """The same rule as `exercise.yaml`'s `extra="forbid"`: a key the author
    clearly meant, silently ignored, is the most expensive kind of content bug.
    """
    document = dict(a_manifest())
    document["order"] = "alphabetical"

    write(library, document)

    assert problems(library) == ("unknown key(s): order",)


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("name", "needs a name"),
        ("title", "needs a title"),
        ("exercises", "needs a non-empty 'exercises' list"),
    ],
)
def test_a_track_missing_a_field_is_refused(
    library: Path, field: str, expected: str
) -> None:
    track = dict(a_manifest()["tracks"][0])  # type: ignore[index]
    del track[field]

    write(library, {"tracks": [track]})

    assert expected in problems(library)[0]


def test_an_id_that_is_not_an_exercise_id_is_refused(library: Path) -> None:
    """Validated through `ExerciseId`, so the two-segment rule has one home —
    restating it here as a pattern would be a second place for it to be wrong.
    """
    write(library, a_manifest(exercises=["git/amend-the-last-commit", "nonsense"]))

    (problem,) = problems(library)
    assert "nonsense" in problem


def test_every_problem_is_reported_rather_than_the_first(library: Path) -> None:
    """Same reason as `validate_exercise`: fixing one typo per run to discover
    the next is a bad way to spend an afternoon.
    """
    write(
        library,
        {
            "tracks": [
                {"name": "a", "title": "First", "exercises": ["nonsense"]},
                {"name": "", "title": "Second", "exercises": ["git/one"]},
            ]
        },
    )

    assert len(problems(library)) == 2
