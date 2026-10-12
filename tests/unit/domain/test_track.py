"""`Track` — an ordered run of exercises with a name it can be followed by.

Two things are worth holding it to. The invariants, because every reader of a
track assumes them: a use case walking one does not check that it has a first
step, or that an exercise sits at one position rather than two. And `after`,
because it is the order *what next* is searched in — the difference between a
Next button that moves on and one that hands back the exercise just failed.
"""

from __future__ import annotations

import pytest

from practice.domain.errors import InvalidValueError
from practice.domain.ids import ExerciseId
from practice.domain.track import Track

ONE = ExerciseId("katas/one")
TWO = ExerciseId("katas/two")
THREE = ExerciseId("katas/three")
FOUR = ExerciseId("katas/four")


def a_track(
    *exercises: ExerciseId, name: str = "blind-75", title: str = "The Blind 75"
) -> Track:
    return Track(
        name=name,
        title=title,
        summary="Seventy-five of them.",
        exercises=exercises or (ONE, TWO, THREE, FOUR),
    )


# --- what a track refuses to be ---------------------------------------------


@pytest.mark.parametrize("name", ["", "Blind 75", "blind_75", "-blind", "blind-"])
def test_a_name_that_could_not_be_a_url_segment_is_refused(name: str) -> None:
    """The name ends up in `/tracks/<name>` and in a form field, so it is held
    to the same slug shape an exercise id's segments are.
    """
    with pytest.raises(InvalidValueError, match="kebab-case"):
        a_track(name=name)


def test_a_track_needs_a_title() -> None:
    with pytest.raises(InvalidValueError, match="needs a title"):
        a_track(title="   ")


def test_a_track_with_nothing_on_it_is_refused() -> None:
    """It would have no first step and no next one, and every reader of a track
    assumes both.
    """
    with pytest.raises(InvalidValueError, match="no exercises"):
        Track(name="empty", title="Empty", summary="Nothing.", exercises=())


def test_an_exercise_listed_twice_is_refused_and_named() -> None:
    """Two positions for one exercise would make `position` pick one and make
    `after` walk past the same step twice.
    """
    with pytest.raises(InvalidValueError, match="lists twice: katas/one"):
        a_track(ONE, TWO, ONE)


# --- asking a track about an exercise ---------------------------------------


def test_it_knows_how_long_it_is_and_what_is_on_it() -> None:
    track = a_track(ONE, TWO)

    assert len(track) == 2
    assert ONE in track
    assert THREE not in track


def test_position_counts_from_zero() -> None:
    track = a_track()

    assert track.position(ONE) == 0
    assert track.position(FOUR) == 3


def test_an_exercise_that_is_not_on_the_track_has_no_position() -> None:
    """`None`, not a raise: whether an exercise is on a track is an ordinary
    question with an ordinary no.
    """
    assert a_track(ONE, TWO).position(THREE) is None


# --- the order what-next is searched in --------------------------------------


def test_after_starts_with_the_step_that_follows() -> None:
    assert a_track().after(TWO)[0] == THREE


def test_after_wraps_round_to_the_steps_that_were_skipped() -> None:
    """Somebody who skipped step one and has just finished step three is sent
    on to four and then back to one, not told there is nothing left.
    """
    assert a_track().after(THREE) == (FOUR, ONE, TWO)


def test_after_never_offers_the_exercise_it_was_asked_about() -> None:
    """The property the Next button rests on. A solver who has just failed a
    step and pressed Next asked to move on, and the first unfinished step from
    the top would be the one they are leaving.
    """
    track = a_track()

    for exercise_id in track.exercises:
        assert exercise_id not in track.after(exercise_id)
        assert len(track.after(exercise_id)) == len(track) - 1


def test_after_the_last_step_is_everything_before_it() -> None:
    assert a_track().after(FOUR) == (ONE, TWO, THREE)


def test_after_an_exercise_that_is_not_on_the_track_is_the_whole_track() -> None:
    """Nothing comes before it, so the search starts at the top."""
    assert a_track(ONE, TWO).after(THREE) == (ONE, TWO)
