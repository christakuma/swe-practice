"""Which exercises are done, where that leaves a track, and what comes next.

The pure half first -- `records_of`, `follow`, `choose` and the three readings
on `TrackProgress` -- against attempts built through the storage door, so a
case can say "failed on the 3rd, passed on the 5th" in two lines. Then the three
use cases over the in-memory stores, which is where the claim that matters is
made: **progress is read off what was graded, never off what was scheduled.**

That claim is why this module exists. The history was complete from Phase 6 and
the product could not be asked about it by exercise, so a solved exercise went
on being offered as new until a schedule button was pressed.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from practice.application.tracks import (
    Record,
    Step,
    TrackProgress,
    choose,
    follow,
    records_of,
)
from practice.application.use_cases import (
    FollowTracks,
    NextExercise,
    RecallExercises,
)
from practice.domain.exercise import Variant
from practice.domain.ids import ExerciseId
from practice.domain.track import Track
from tests.fakes import a_kata
from tests.unit.application.helpers import (
    a_review_queue,
    a_start_attempt,
    a_submit_solution,
    an_environment,
)
from tests.unit.application.test_progress import abandoned, finished

if TYPE_CHECKING:
    from practice.domain.attempt import Attempt
    from practice.domain.exercise import Exercise
    from tests.unit.application.helpers import World

ONE = a_kata(exercise_id="katas/one")
TWO = a_kata(exercise_id="katas/two")
THREE = a_kata(exercise_id="katas/three")
FOUR = a_kata(exercise_id="katas/four")
LIBRARY = (ONE, TWO, THREE, FOUR)

THE_3RD = date(2026, 10, 3)
THE_5TH = date(2026, 10, 5)
THE_7TH = date(2026, 10, 7)


def a_track(*exercises: Exercise, name: str = "katas") -> Track:
    return Track(
        name=name,
        title=name.title(),
        summary="A few katas.",
        exercises=tuple(exercise.id for exercise in exercises or LIBRARY),
    )


def a_walk(*attempts: Attempt, track: Track | None = None) -> TrackProgress:
    return follow(
        track if track is not None else a_track(),
        exercises={exercise.id: exercise for exercise in LIBRARY},
        records=records_of(attempts),
    )


def ended_at(day: date) -> datetime:
    """When `finished(..., day=day)` ends: 09:00 plus its ten minutes."""
    return datetime(day.year, day.month, day.day, 9, 10, tzinfo=UTC)


# --- what the history says about one exercise --------------------------------


def test_an_exercise_never_attempted_has_no_record() -> None:
    """The absence is the state. A record with a zero in it would be a second
    way of saying the same thing, and every list would have to check both.
    """
    assert records_of(()) == {}
    assert ONE.id not in records_of([finished(TWO)])


def test_a_pass_is_recorded_with_the_day_it_happened() -> None:
    """*Which have I done and when* -- both halves, from one attempt."""
    record = records_of([finished(ONE, day=THE_5TH)])[ONE.id]

    assert record == Record(
        attempts=1,
        passes=1,
        last_attempted_at=ended_at(THE_5TH),
        last_passed_at=ended_at(THE_5TH),
    )
    assert record.is_done


def test_an_exercise_only_ever_failed_is_attempted_and_not_done() -> None:
    """The row most worth finding in a list: not new, and not finished."""
    record = records_of([finished(ONE, day=THE_3RD, passed=False)])[ONE.id]

    assert record.attempts == 1
    assert record.passes == 0
    assert record.last_passed_at is None
    assert record.last_attempted_at == ended_at(THE_3RD)
    assert not record.is_done


def test_a_later_failure_does_not_undo_a_pass() -> None:
    """Done means passed once, and stays meant. The failure is still visible --
    it is the last attempt -- but a route whose finished steps reopened behind
    you would be one nobody could finish. Noticing forgetting is the
    scheduler's job.
    """
    record = records_of(
        [
            finished(ONE, day=THE_3RD),
            finished(ONE, day=THE_5TH, passed=False),
        ]
    )[ONE.id]

    assert record.is_done
    assert record.attempts == 2
    assert record.passes == 1
    assert record.last_passed_at == ended_at(THE_3RD)
    assert record.last_attempted_at == ended_at(THE_5TH)


def test_the_dates_are_the_latest_whatever_order_the_attempts_arrive_in() -> None:
    """The repository answers oldest first, and nothing here leans on it: the
    same three attempts reversed reduce to the same record.
    """
    attempts = [
        finished(ONE, day=THE_3RD),
        finished(ONE, day=THE_7TH),
        finished(ONE, day=THE_5TH, passed=False),
    ]

    forwards = records_of(attempts)[ONE.id]
    backwards = records_of(reversed(attempts))[ONE.id]

    assert forwards == backwards
    assert forwards.last_passed_at == ended_at(THE_7TH)
    assert forwards.last_attempted_at == ended_at(THE_7TH)
    assert forwards.passes == 2


def test_an_attempt_that_was_never_graded_is_not_counted() -> None:
    """Abandoned: an end and no verdict. Counting it would make an exercise
    somebody gave up on look attempted-and-failed.
    """
    assert records_of([abandoned(ONE)]) == {}


def test_each_exercise_gets_its_own_record() -> None:
    records = records_of([finished(ONE), finished(TWO, passed=False)])

    assert records[ONE.id].is_done
    assert not records[TWO.id].is_done


# --- a track, walked ----------------------------------------------------------


def test_every_step_is_numbered_from_one_in_the_tracks_order() -> None:
    walk = a_walk(track=a_track(THREE, ONE))

    assert [(step.number, step.exercise.id) for step in walk.steps] == [
        (1, THREE.id),
        (2, ONE.id),
    ]


def test_a_fresh_track_has_nothing_done_and_starts_at_the_top() -> None:
    walk = a_walk()

    assert (walk.done, walk.total) == (0, 4)
    assert not walk.is_complete
    assert walk.next_up == Step(number=1, exercise=ONE)


def test_next_up_is_the_first_step_not_yet_passed() -> None:
    """*Continue*, for somebody coming back: past what is done, and a failed
    step is not done.
    """
    walk = a_walk(finished(ONE), finished(TWO, passed=False))

    assert walk.done == 1
    assert walk.next_up is not None
    assert walk.next_up.exercise.id == TWO.id


def test_a_step_carries_what_the_history_says_of_it() -> None:
    walk = a_walk(finished(TWO, day=THE_5TH))

    assert walk.steps[0].record is None
    assert not walk.steps[0].is_done
    assert walk.steps[1].record is not None
    assert walk.steps[1].record.last_passed_at == ended_at(THE_5TH)
    assert walk.steps[1].is_done


def test_a_track_with_every_step_passed_is_complete() -> None:
    walk = a_walk(*(finished(exercise) for exercise in LIBRARY))

    assert walk.is_complete
    assert walk.next_up is None
    assert walk.after(ONE.id) is None


def test_a_step_whose_exercise_has_left_the_library_is_left_out() -> None:
    """A library edited under a running server. The track is shown one step
    short, and the steps that remain keep the numbers the track gives them --
    step four is still called four.
    """
    walk = follow(
        a_track(),
        exercises={exercise.id: exercise for exercise in (ONE, TWO, FOUR)},
        records={},
    )

    assert [step.number for step in walk.steps] == [1, 2, 4]
    assert walk.total == 3


def test_a_track_with_no_steps_left_is_not_complete() -> None:
    """Emptied, not finished. `all()` of nothing is true, and a page that
    congratulated somebody on a track whose exercises were all deleted would be
    reporting that as an achievement.
    """
    walk = follow(a_track(), exercises={}, records={})

    assert walk.steps == ()
    assert not walk.is_complete
    assert walk.next_up is None


# --- the step after this one --------------------------------------------------


def test_after_a_pass_comes_the_following_step() -> None:
    walk = a_walk(finished(ONE))

    found = walk.after(ONE.id)

    assert found is not None
    assert (found.number, found.exercise.id) == (2, TWO.id)


def test_after_a_failure_comes_the_following_step_and_not_the_same_one() -> None:
    """The case `next_up` gets wrong and the reason `after` exists: the first
    unfinished step from the top *is* the one just failed.
    """
    walk = a_walk(finished(ONE), finished(TWO, passed=False))

    assert walk.next_up is not None
    assert walk.next_up.exercise.id == TWO.id
    found = walk.after(TWO.id)
    assert found is not None
    assert found.exercise.id == THREE.id


def test_after_skips_steps_that_are_already_done() -> None:
    walk = a_walk(finished(ONE), finished(TWO), finished(THREE))

    found = walk.after(ONE.id)

    assert found is not None
    assert found.exercise.id == FOUR.id


def test_after_the_last_step_wraps_to_one_that_was_skipped() -> None:
    walk = a_walk(finished(ONE), finished(THREE), finished(FOUR))

    found = walk.after(FOUR.id)

    assert found is not None
    assert (found.number, found.exercise.id) == (2, TWO.id)


def test_after_the_only_unfinished_step_there_is_nothing() -> None:
    """Not quite `is_complete`: the exercise asked about is never its own
    successor, so a solver who has just failed the last unfinished step is told
    nothing else is left rather than handed it back.
    """
    walk = a_walk(finished(ONE), finished(TWO), finished(THREE))

    assert not walk.is_complete
    assert walk.after(FOUR.id) is None


def test_after_an_exercise_that_is_not_on_the_track_is_the_first_unfinished() -> None:
    """Somebody wandered off to an exercise from Browse and pressed Next: they
    are sent back to where they were on the track.
    """
    walk = a_walk(finished(ONE), track=a_track(ONE, TWO, THREE))

    found = walk.after(FOUR.id)

    assert found is not None
    assert found.exercise.id == TWO.id


def test_after_passes_over_a_step_the_library_no_longer_holds() -> None:
    walk = follow(
        a_track(),
        exercises={exercise.id: exercise for exercise in (ONE, THREE)},
        records={},
    )

    found = walk.after(ONE.id)

    assert found is not None
    assert found.exercise.id == THREE.id


# --- which track ---------------------------------------------------------------


def test_the_named_track_is_chosen() -> None:
    first, second = a_track(name="everything"), a_track(name="blind-75")

    assert choose([first, second], "blind-75") is second


def test_with_no_name_the_first_track_is_the_default() -> None:
    """`ContentRepository.list_tracks` documents the first track as the default,
    and this is where that is true.
    """
    first, second = a_track(name="everything"), a_track(name="blind-75")

    assert choose([first, second], None) is first


def test_a_name_that_matches_nothing_falls_back_to_the_first() -> None:
    """A stale link to a renamed track still gets a Next button."""
    first = a_track(name="everything")

    assert choose([first], "renamed-since") is first


def test_a_library_with_no_tracks_has_none_to_choose() -> None:
    assert choose([], "blind-75") is None
    assert choose([], None) is None


# --- the use cases -------------------------------------------------------------


def a_world(*tracks: Track) -> World:
    """The four katas, and whichever tracks a test is about."""
    world = an_environment()
    world.content.add(*LIBRARY)
    world.content.offer(*tracks)
    return world


def solve(world: World, exercise: Exercise) -> None:
    """Start and submit through the real use cases; the default grader passes."""
    started = a_start_attempt(world)(exercise.id)
    a_submit_solution(world)(started.attempt.id, "def solve(): ...\n")


def test_recall_reports_what_was_graded() -> None:
    world = a_world()
    solve(world, TWO)

    records = RecallExercises(attempts=world.attempts)()

    assert set(records) == {TWO.id}
    assert records[TWO.id].is_done
    assert records[TWO.id].last_passed_at == world.clock.now()


def test_recall_does_not_count_an_attempt_that_is_still_open() -> None:
    world = a_world()
    a_start_attempt(world)(ONE.id)

    assert RecallExercises(attempts=world.attempts)() == {}


def test_an_exercise_solved_and_never_scheduled_is_still_recalled() -> None:
    """**The defect this phase was for, stated as a test.** Nothing presses a
    schedule button here, so there is no card and the due queue still offers the
    exercise as new -- which was every surface's only source of status. The
    attempt log knows better, and this is the read that asks it.
    """
    world = a_world()
    solve(world, ONE)

    queue = {row.exercise.id: row for row in a_review_queue(world)()}
    records = RecallExercises(attempts=world.attempts)()

    assert queue[ONE.id].is_new
    assert records[ONE.id].is_done


def test_following_walks_every_declared_track_in_declared_order() -> None:
    world = a_world(a_track(name="everything"), a_track(TWO, ONE, name="short"))
    solve(world, ONE)

    everything, short = FollowTracks(content=world.content, attempts=world.attempts)()

    assert (everything.track.name, everything.done, everything.total) == (
        "everything",
        1,
        4,
    )
    assert (short.track.name, short.done, short.total) == ("short", 1, 2)
    assert short.next_up is not None
    assert short.next_up.exercise.id == TWO.id


def test_following_a_library_with_no_tracks_finds_none() -> None:
    world = a_world()

    assert FollowTracks(content=world.content, attempts=world.attempts)() == ()


def test_next_is_the_step_after_this_one_on_the_named_track() -> None:
    world = a_world(a_track(name="everything"), a_track(THREE, ONE, TWO, name="odd"))
    solve(world, ONE)

    upcoming = NextExercise(content=world.content, attempts=world.attempts)(
        ONE.id, "odd"
    )

    assert upcoming is not None
    assert upcoming.progress.track.name == "odd"
    assert upcoming.step is not None
    assert (upcoming.step.number, upcoming.step.exercise.id) == (3, TWO.id)


def test_next_follows_the_first_track_when_none_is_named() -> None:
    """An attempt started from Browse. The default is the library's choice --
    whatever it declares first -- and here it is the one in the other order.
    """
    world = a_world(a_track(name="everything"), a_track(THREE, ONE, TWO, name="odd"))
    solve(world, ONE)

    upcoming = NextExercise(content=world.content, attempts=world.attempts)(ONE.id)

    assert upcoming is not None
    assert upcoming.progress.track.name == "everything"
    assert upcoming.step is not None
    assert upcoming.step.exercise.id == TWO.id


def test_next_moves_on_without_a_schedule_grade() -> None:
    """Why this follows a track and not the due queue. Two exercises solved and
    neither scheduled: the queue still lists both, so its head is the first
    thing solved. The track asks the attempt log and offers the third.
    """
    world = a_world(a_track())
    solve(world, ONE)
    solve(world, TWO)

    upcoming = NextExercise(content=world.content, attempts=world.attempts)(TWO.id)

    still_queued = [row.exercise.id for row in a_review_queue(world)()]
    assert ONE.id in still_queued
    assert TWO.id in still_queued
    assert upcoming is not None
    assert upcoming.step is not None
    assert upcoming.step.exercise.id == THREE.id


def test_next_after_a_variant_is_the_step_after_its_base() -> None:
    """A variant is on no track (ADR 0028), so asked about by its own id it is
    an exercise somebody wandered off to, and the answer was the first
    unfinished step from the top -- step one, for a solver who chose the twist
    on step three from the track's own page.
    """
    twist = a_kata(
        exercise_id="variants/three-backwards",
        variant=Variant(of=THREE.id, twist="Read it from the other end."),
    )
    world = a_world(a_track())
    world.content.add(twist)
    solve(world, twist)

    upcoming = NextExercise(content=world.content, attempts=world.attempts)(twist.id)

    assert upcoming is not None
    assert upcoming.step is not None
    assert upcoming.step.exercise.id == FOUR.id


def test_next_after_a_variant_comes_back_round_to_its_base() -> None:
    """Starting after the base is not skipping it. An exercise is never its
    own successor, but the twist is not the base -- so when everything else is
    done the standard version is what is left, and it is offered.
    """
    twist = a_kata(
        exercise_id="variants/two-backwards",
        variant=Variant(of=TWO.id, twist="Read it from the other end."),
    )
    world = a_world(a_track(ONE, TWO))
    world.content.add(twist)
    solve(world, ONE)
    solve(world, twist)

    upcoming = NextExercise(content=world.content, attempts=world.attempts)(twist.id)

    assert upcoming is not None
    assert upcoming.step is not None
    assert upcoming.step.exercise.id == TWO.id


def test_next_on_a_finished_track_says_which_track_ran_out() -> None:
    """An answer, not an absence: the page needs the track to say it is done."""
    world = a_world(a_track(ONE, TWO))
    solve(world, ONE)
    solve(world, TWO)

    upcoming = NextExercise(content=world.content, attempts=world.attempts)(TWO.id)

    assert upcoming is not None
    assert upcoming.step is None
    assert upcoming.progress.is_complete


def test_there_is_no_next_in_a_library_with_no_tracks() -> None:
    world = a_world()

    assert (
        NextExercise(content=world.content, attempts=world.attempts)(
            ExerciseId("katas/one")
        )
        is None
    )
