"""`tracks.yaml` — the routes through a library, from the file to the port.

Four things are held here, in the order a track travels. The **parser**, which
has two spellings to accept and a longer list of things to refuse. **Resolving**
a declaration against a library, where *follow the curriculum* becomes ids.
**`practice validate`**, which is where the claim that a track's order makes
sense is enforced rather than asserted. And a **pack**, which has to carry the
file narrowed to its own exercises or install to a root that validation refuses.

The validation tests are the ones written against ADR 0022's warning. Each
ordering case is paired with the same library in the *other* order, so the rule
is seen to fire and seen not to -- a rule that only ever passed in its tests
would be indistinguishable from one that checked nothing.
"""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import pytest
import yaml

from practice.adapters.content import (
    ContentError,
    FilesystemContentRepository,
    PackContentRepository,
    install_pack,
    validate_library,
    write_pack,
)
from practice.adapters.content.tracks import (
    TRACKS_FILENAME,
    TrackDeclaration,
    load_tracks,
    narrow_tracks,
    parse_tracks,
    render_tracks,
    resolve_tracks,
)
from practice.domain.ids import ExerciseId

from ..conftest import a_drill, a_kata, a_scenario

if TYPE_CHECKING:
    from pathlib import Path

    from ..conftest import WriteExercise

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/undo-a-commit")
DRILL = ExerciseId("sql/one-row-per-customer")


def a_declaration(**overrides: object) -> dict[str, object]:
    """One valid explicit track, as the YAML spells it."""
    document: dict[str, object] = {
        "name": "blind-75",
        "title": "The Blind 75",
        "summary": "Seventy-five of them, in a sensible order.",
        "exercises": [KATA.value, SCENARIO.value],
    }
    document.update(overrides)
    return {key: value for key, value in document.items() if value is not None}


def write_tracks(library: Path, *tracks: object) -> Path:
    path = library / TRACKS_FILENAME
    path.write_text(
        yaml.safe_dump({"tracks": list(tracks)}, sort_keys=False), encoding="utf-8"
    )
    return path


def problems_with(*tracks: object) -> tuple[str, ...]:
    """What the parser says about a document, or `()` if it accepts it."""
    try:
        parse_tracks(yaml.safe_dump({"tracks": list(tracks)}), located_at="tracks.yaml")
    except ContentError as exc:
        return tuple(exc.problems)
    return ()


# --- the two spellings ---------------------------------------------------------


def test_an_explicit_track_lists_its_exercises_in_order() -> None:
    (declared,) = parse_tracks(
        yaml.safe_dump({"tracks": [a_declaration()]}), located_at="tracks.yaml"
    )

    assert declared == TrackDeclaration(
        name="blind-75",
        title="The Blind 75",
        summary="Seventy-five of them, in a sensible order.",
        exercises=(KATA, SCENARIO),
    )
    assert not declared.follows_curriculum


def test_a_track_can_follow_the_curriculum_instead_of_listing_anything() -> None:
    """So the whole-library track is not a copy of the file next door, wrong the
    first time an exercise is added to one and not the other.
    """
    (declared,) = parse_tracks(
        yaml.safe_dump(
            {"tracks": [a_declaration(exercises=None, follows="curriculum")]}
        ),
        located_at="tracks.yaml",
    )

    assert declared.exercises is None
    assert declared.follows_curriculum


def test_tracks_come_back_in_the_order_they_are_declared() -> None:
    """The order is part of the answer: the first track is the default."""
    declared = parse_tracks(
        yaml.safe_dump(
            {
                "tracks": [
                    a_declaration(name="zebra"),
                    a_declaration(name="aardvark"),
                ]
            }
        ),
        located_at="tracks.yaml",
    )

    assert [found.name for found in declared] == ["zebra", "aardvark"]


# --- what the parser refuses -----------------------------------------------------


def test_a_library_with_no_tracks_file_declares_none(library: Path) -> None:
    """Not the missing-curriculum case. Without an order a library cannot be
    listed honestly; without tracks it has only not offered any.
    """
    assert load_tracks(library) == ()


def test_a_file_that_is_present_and_wrong_is_an_error(library: Path) -> None:
    """Declining to offer tracks is a choice. A typo is not."""
    (library / TRACKS_FILENAME).write_text("tracks: [unclosed", encoding="utf-8")

    with pytest.raises(ContentError) as caught:
        load_tracks(library)

    assert "is not valid YAML" in caught.value.problems[0]


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ("- just\n- a list\n", "must be a mapping with a 'tracks' key"),
        ("tracks: []\n", "'tracks' must be a non-empty list"),
        ("tracks: nope\n", "'tracks' must be a non-empty list"),
    ],
)
def test_a_document_of_the_wrong_shape_is_refused(document: str, expected: str) -> None:
    with pytest.raises(ContentError) as caught:
        parse_tracks(document, located_at="tracks.yaml")

    assert caught.value.problems == (expected,)


def test_an_unknown_top_level_key_is_named() -> None:
    with pytest.raises(ContentError) as caught:
        parse_tracks(
            yaml.safe_dump({"tracks": [a_declaration()], "paths": []}),
            located_at="tracks.yaml",
        )

    assert caught.value.problems == ("unknown key(s): paths",)


@pytest.mark.parametrize(
    ("track", "expected"),
    [
        ("not a mapping", "tracks[0]: must be a mapping"),
        (a_declaration(name=None), "tracks[0]: needs a name"),
        (a_declaration(title=None), "blind-75: needs a title"),
        (
            a_declaration(summary="  "),
            "blind-75: needs a summary saying what the track is for",
        ),
        (a_declaration(order="hard"), "blind-75: unknown key(s): order"),
        (
            a_declaration(follows="curriculum"),
            (
                "blind-75: needs exactly one of 'exercises' (a list of ids) or "
                "'follows: curriculum'"
            ),
        ),
        (
            a_declaration(exercises=None),
            (
                "blind-75: needs exactly one of 'exercises' (a list of ids) or "
                "'follows: curriculum'"
            ),
        ),
        (
            a_declaration(exercises=None, follows="alphabet"),
            "blind-75: 'follows' can only name 'curriculum', got 'alphabet'",
        ),
        (
            a_declaration(exercises="katas/two-sum"),
            "blind-75: 'exercises' must be a non-empty list",
        ),
        (a_declaration(exercises=[7]), "blind-75: 7 is not an exercise id"),
        (
            a_declaration(exercises=[KATA.value, KATA.value]),
            "track 'blind-75' lists twice: katas/two-sum",
        ),
        (
            a_declaration(name="Blind 75"),
            "a track's name must be lowercase kebab-case, got 'Blind 75'",
        ),
    ],
)
def test_a_malformed_track_is_refused_by_name(track: object, expected: str) -> None:
    assert problems_with(track) == (expected,)


def test_an_empty_exercises_list_is_refused() -> None:
    """Spelt out beside the table above because YAML makes it easy to miss: an
    empty list is *present*, so it must not be mistaken for "follows instead".
    """
    with pytest.raises(ContentError) as caught:
        parse_tracks(
            "tracks:\n  - name: a\n    title: A\n    summary: s\n    exercises: []\n",
            located_at="tracks.yaml",
        )

    assert caught.value.problems == ("a: 'exercises' must be a non-empty list",)


def test_an_id_that_is_not_an_exercise_id_is_refused_with_the_domains_reason() -> None:
    (problem,) = problems_with(a_declaration(exercises=["not-an-id"]))

    assert problem.startswith("blind-75: 'not-an-id' exercise id must be")


def test_two_tracks_with_one_name_are_refused() -> None:
    """A name is a URL, and `/tracks/blind-75` can only be one page."""
    assert problems_with(a_declaration(), a_declaration()) == (
        "declares twice: blind-75",
    )


def test_every_problem_is_reported_in_one_pass() -> None:
    found = problems_with(
        a_declaration(name="one", title=None),
        a_declaration(name="two", exercises=[7]),
    )

    assert found == ("one: needs a title", "two: 7 is not an exercise id")


# --- resolving against a library --------------------------------------------------


def test_following_the_curriculum_resolves_to_the_library_in_its_order() -> None:
    (track,) = resolve_tracks(
        [TrackDeclaration(name="everything", title="All", summary="All of it.")],
        [SCENARIO, KATA, DRILL],
    )

    assert track.exercises == (SCENARIO, KATA, DRILL)


def test_an_explicit_track_keeps_its_own_order() -> None:
    """Whatever the library's is. This is the freedom a track is for."""
    (track,) = resolve_tracks(
        [
            TrackDeclaration(
                name="mine", title="Mine", summary="s", exercises=(DRILL, SCENARIO)
            )
        ],
        [SCENARIO, KATA, DRILL],
    )

    assert track.exercises == (DRILL, SCENARIO)


def test_an_id_the_library_does_not_hold_is_dropped_at_runtime() -> None:
    """Lenient here and strict in `validate`, like the curriculum: somebody
    halfway through a rename finds a track one step short, not a server that
    will not start.
    """
    (track,) = resolve_tracks(
        [
            TrackDeclaration(
                name="mine", title="Mine", summary="s", exercises=(KATA, DRILL)
            )
        ],
        [KATA],
    )

    assert track.exercises == (KATA,)


def test_a_track_left_with_nothing_on_it_is_not_offered() -> None:
    declared = [
        TrackDeclaration(name="gone", title="Gone", summary="s", exercises=(DRILL,)),
        TrackDeclaration(name="everything", title="All", summary="s"),
    ]

    assert [track.name for track in resolve_tracks(declared, [KATA])] == ["everything"]
    assert resolve_tracks(declared, []) == ()


# --- the filesystem repository ------------------------------------------------------


def test_the_repository_lists_tracks_resolved_against_its_own_order(
    library: Path, write_exercise: WriteExercise
) -> None:
    """Written scenario first, so the curriculum is scenario-then-kata, and the
    track that follows it comes back in that order rather than by id.
    """
    write_exercise(a_scenario())
    write_exercise(a_kata())
    write_tracks(
        library,
        a_declaration(name="everything", exercises=None, follows="curriculum"),
        a_declaration(name="katas-only", exercises=[KATA.value]),
    )

    everything, katas = FilesystemContentRepository(library).list_tracks()

    assert (everything.name, everything.exercises) == ("everything", (SCENARIO, KATA))
    assert (katas.name, katas.exercises) == ("katas-only", (KATA,))


def test_a_repository_over_a_library_with_no_tracks_file_lists_none(
    library: Path, write_exercise: WriteExercise
) -> None:
    write_exercise(a_kata())

    assert FilesystemContentRepository(library).list_tracks() == ()


def test_the_tracks_are_read_once(library: Path, write_exercise: WriteExercise) -> None:
    """Cached, like the exercises: content is read-only at runtime."""
    write_exercise(a_kata())
    path = write_tracks(library, a_declaration(exercises=[KATA.value]))
    repository = FilesystemContentRepository(library)

    first = repository.list_tracks()
    path.unlink()

    assert repository.list_tracks() is first


# --- what `practice validate` holds a track to ---------------------------------------


def two_sections(library: Path, write_exercise: WriteExercise) -> None:
    """Four exercises in two curriculum sections: `first` then `second`.

    The shape the ordering rule needs to be seen against. Inside `trees` the
    order is dependency; between the two sections a track is free.
    """
    for exercise_id in ("katas/tree-one", "katas/tree-two"):
        write_exercise(a_kata(id=exercise_id), curriculum=False)
    for exercise_id in ("katas/graph-one", "katas/graph-two"):
        write_exercise(a_kata(id=exercise_id), curriculum=False)
    (library / "curriculum.yaml").write_text(
        yaml.safe_dump(
            {
                "tracks": [
                    {
                        "name": "trees",
                        "title": "Trees",
                        "exercises": ["katas/tree-one", "katas/tree-two"],
                    },
                    {
                        "name": "graphs",
                        "title": "Graphs",
                        "exercises": ["katas/graph-one", "katas/graph-two"],
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_a_library_with_no_tracks_file_validates(
    library: Path, write_exercise: WriteExercise
) -> None:
    write_exercise(a_kata())

    assert validate_library(library).ok


def test_a_track_in_the_curriculums_own_order_validates(
    library: Path, write_exercise: WriteExercise
) -> None:
    two_sections(library, write_exercise)
    write_tracks(
        library,
        a_declaration(
            exercises=[
                "katas/tree-one",
                "katas/tree-two",
                "katas/graph-one",
                "katas/graph-two",
            ]
        ),
    )

    assert validate_library(library).problems == ()


def test_a_track_may_put_whole_sections_in_an_order_of_its_own(
    library: Path, write_exercise: WriteExercise
) -> None:
    """Graphs before trees, and the two interleaved: both are between-section
    moves, which is the freedom the Blind 75 and the git track both use.
    """
    two_sections(library, write_exercise)
    write_tracks(
        library,
        a_declaration(
            exercises=[
                "katas/graph-one",
                "katas/tree-one",
                "katas/graph-two",
                "katas/tree-two",
            ]
        ),
    )

    assert validate_library(library).problems == ()


def test_a_track_may_not_reverse_two_exercises_inside_one_section(
    library: Path, write_exercise: WriteExercise
) -> None:
    """**The rule the word *sensible* rests on.** Inside a section the
    curriculum's order is dependency (ADR 0014), so a track that offers the
    second before the first is offering a lesson before its premise. The same
    four exercises as the two tests above, with one pair swapped.
    """
    two_sections(library, write_exercise)
    write_tracks(
        library,
        a_declaration(
            exercises=[
                "katas/tree-two",
                "katas/tree-one",
                "katas/graph-one",
                "katas/graph-two",
            ]
        ),
    )

    assert validate_library(library).problems == (
        (
            "tracks.yaml: blind-75: puts katas/tree-two before katas/tree-one, and "
            "curriculum.yaml orders them the other way inside 'trees'"
        ),
    )


def test_a_reversal_is_found_when_the_track_skips_the_exercises_between(
    library: Path, write_exercise: WriteExercise
) -> None:
    """A track that *selects* is still held to the order of what it kept: three
    in a section, the middle one left out, the outer two swapped.
    """
    for exercise_id in ("katas/a", "katas/b", "katas/c"):
        write_exercise(a_kata(id=exercise_id))
    write_tracks(library, a_declaration(exercises=["katas/c", "katas/a"]))

    assert validate_library(library).problems == (
        (
            "tracks.yaml: blind-75: puts katas/c before katas/a, and curriculum.yaml "
            "orders them the other way inside 'everything'"
        ),
    )


def test_a_track_that_names_an_exercise_not_on_disk_is_reported(
    library: Path, write_exercise: WriteExercise
) -> None:
    write_exercise(a_kata())
    write_tracks(library, a_declaration(exercises=[KATA.value, "katas/renamed-since"]))

    assert validate_library(library).problems == (
        (
            "tracks.yaml: blind-75: lists exercise(s) that are not on disk: "
            "katas/renamed-since"
        ),
    )


def test_a_malformed_tracks_file_is_reported_under_its_own_name(
    library: Path, write_exercise: WriteExercise
) -> None:
    write_exercise(a_kata())
    write_tracks(library, a_declaration(title=None))

    assert validate_library(library).problems == (
        "tracks.yaml: blind-75: needs a title",
    )


def test_a_track_that_follows_the_curriculum_is_not_examined(
    library: Path, write_exercise: WriteExercise
) -> None:
    """It cannot name a missing exercise or contradict an order it is."""
    write_exercise(a_kata())
    write_tracks(library, a_declaration(exercises=None, follows="curriculum"))

    assert validate_library(library).problems == ()


def test_a_broken_curriculum_is_reported_once_and_the_tracks_still_checked(
    library: Path, write_exercise: WriteExercise
) -> None:
    """With no order there is nothing to hold a track's order against, so that
    half is skipped rather than raised about -- and the half that needs no
    curriculum still runs.
    """
    write_exercise(a_kata())
    (library / "curriculum.yaml").write_text("tracks: [unclosed", encoding="utf-8")
    write_tracks(library, a_declaration(exercises=[KATA.value, "katas/missing"]))

    found = validate_library(library).problems

    assert len([problem for problem in found if "curriculum.yaml" in problem]) == 1
    assert found[-1] == (
        "tracks.yaml: blind-75: lists exercise(s) that are not on disk: katas/missing"
    )


# --- a pack carries its tracks --------------------------------------------------------


@pytest.fixture
def stocked(library: Path, write_exercise: WriteExercise) -> Path:
    """One of each kind, a whole-library track and one that selects two."""
    write_exercise(a_scenario())
    write_exercise(a_kata())
    write_exercise(a_drill())
    write_tracks(
        library,
        a_declaration(name="everything", exercises=None, follows="curriculum"),
        a_declaration(name="no-sql", exercises=[SCENARIO.value, KATA.value]),
        a_declaration(name="sql-only", exercises=[DRILL.value]),
    )
    return library


def packed(tmp_path: Path, root: Path, *keep: ExerciseId) -> Path:
    """A pack of `keep`, or of the whole library when nothing is named."""
    exercises = [
        exercise
        for exercise in FilesystemContentRepository(root).list_exercises()
        if not keep or exercise.id in keep
    ]
    destination = tmp_path / "out.practicepack"
    write_pack(destination, content_root=root, exercises=exercises)
    return destination


def test_narrowing_removes_what_was_not_selected_and_drops_an_emptied_track() -> None:
    declared = (
        TrackDeclaration(name="everything", title="All", summary="s"),
        TrackDeclaration(
            name="mixed", title="Mixed", summary="s", exercises=(KATA, DRILL)
        ),
        TrackDeclaration(name="sql", title="SQL", summary="s", exercises=(DRILL,)),
    )

    narrowed = narrow_tracks(declared, {KATA})

    assert [(found.name, found.exercises) for found in narrowed] == [
        ("everything", None),
        ("mixed", (KATA,)),
    ]


def test_rendered_tracks_parse_back_to_what_was_rendered() -> None:
    """The pack writes with one function and reads with the other, so the round
    trip is the property -- including a title with a character YAML would
    otherwise escape.
    """
    declared = (
        TrackDeclaration(
            name="everything", title="Everything — all of it", summary="s"
        ),
        TrackDeclaration(
            name="mixed", title="Mixed: two", summary="s", exercises=(KATA, DRILL)
        ),
    )

    rendered = render_tracks(declared, header="# derived\n")

    assert rendered.startswith(b"# derived\n")
    assert parse_tracks(rendered.decode("utf-8"), located_at="tracks.yaml") == declared


def test_a_pack_of_the_whole_library_carries_every_track(
    tmp_path: Path, stocked: Path
) -> None:
    tracks = PackContentRepository(packed(tmp_path, stocked)).list_tracks()

    assert [(track.name, track.exercises) for track in tracks] == [
        ("everything", (SCENARIO, KATA, DRILL)),
        ("no-sql", (SCENARIO, KATA)),
        ("sql-only", (DRILL,)),
    ]


def test_a_subset_pack_narrows_its_tracks(tmp_path: Path, stocked: Path) -> None:
    """The finding the pack format turned on, a second time: a pack that copied
    the source library's whole `tracks.yaml` would install to a root
    `practice validate` refuses, naming exercises that are not there.
    """
    tracks = PackContentRepository(packed(tmp_path, stocked, KATA)).list_tracks()

    assert [(track.name, track.exercises) for track in tracks] == [
        ("everything", (KATA,)),
        ("no-sql", (KATA,)),
    ]


def test_a_pack_and_the_directory_it_came_from_agree_about_tracks(
    tmp_path: Path, stocked: Path
) -> None:
    """One parser and one resolver behind both repositories, which is the claim
    `ContentRepository`'s second implementation exists to test.
    """
    from_directory = FilesystemContentRepository(stocked).list_tracks()
    from_pack = PackContentRepository(packed(tmp_path, stocked)).list_tracks()

    assert tuple(from_pack) == tuple(from_directory)


def test_a_pack_from_a_library_with_no_tracks_carries_no_tracks_file(
    tmp_path: Path, library: Path, write_exercise: WriteExercise
) -> None:
    """Absent rather than empty: the parser refuses an empty list, and every
    pack written before this file existed has none either.
    """
    write_exercise(a_kata())
    destination = packed(tmp_path, library)

    with zipfile.ZipFile(destination) as archive:
        assert TRACKS_FILENAME not in archive.namelist()
    assert PackContentRepository(destination).list_tracks() == ()


def test_an_installed_pack_validates_and_offers_its_tracks(
    tmp_path: Path, stocked: Path
) -> None:
    """End to end: narrowed on the way out, verified on the way in, and the
    root it lands in passes the audit the install step tells you to run.
    """
    root = tmp_path / "installed"
    install_pack(packed(tmp_path, stocked, KATA, SCENARIO), root)

    assert validate_library(root).problems == ()
    assert [
        track.name for track in FilesystemContentRepository(root).list_tracks()
    ] == [
        "everything",
        "no-sql",
    ]
