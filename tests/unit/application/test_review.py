"""`OfferReview`, `GradeReview` and `ReviewQueue`: the scheduling group.

What these pin down is the part the domain tests cannot: that the suggestion the
panel shows is the one the post applies, that one attempt moves a card once, and
that the queue answers the question §11 makes the phase's exit — *what should I
practise today* — on a store where almost nothing has been scheduled yet.

The scheduler here is `FixedScheduler`, which records the grade it was handed
rather than running SM-2. A test about *which* grade reached the scheduler must
not also depend on the intervals, or the next change to the learning steps breaks
a file that has nothing to do with them.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import pytest

from practice.application.dto import DueExercise, ReviewOffer
from practice.application.errors import AttemptNotFoundError, ExerciseNotFoundError
from practice.domain.errors import AttemptStateError
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.review import CardState, Grade, ReviewCard
from practice.domain.scheduling import GradeSuggestion, suggest_grade
from tests.fakes import a_kata
from tests.unit.application.helpers import (
    RecordingGrader,
    World,
    a_failing_verdict,
    a_grade_review,
    a_review_queue,
    a_start_attempt,
    a_submit_solution,
    an_environment,
    an_offer_review,
)

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
MISSING = AttemptId.parse("00000000-0000-4000-8000-00000000dead")


def a_graded_attempt(world: World) -> AttemptId:
    """Start a kata and submit it, so there is something to review.

    Through the real use cases rather than by constructing an `Attempt`: the
    thing under test reads a *stored* attempt, and a hand-built one would skip
    the save that makes it readable.
    """
    attempt_id = a_start_attempt(world)(KATA).attempt.id
    a_submit_solution(world)(attempt_id, "def two_sum(...): ...")
    return attempt_id


def a_failing_world() -> World:
    """A world whose kata grader fails. Chosen before the environment is built,
    because a grader swapped afterwards would make every test in the file depend
    on the order they ran in.
    """
    return an_environment(grader=RecordingGrader(a_failing_verdict()))


# --- OfferReview -----------------------------------------------------------


class TestOfferReview:
    def test_it_reads_the_suggestion_off_the_attempt(self) -> None:
        world = an_environment()
        attempt_id = a_graded_attempt(world)

        offer = an_offer_review(world)(attempt_id)

        assert offer.suggested is Grade.EASY
        assert offer.suggestion.is_clean is True
        assert offer.exercise.id == KATA

    def test_the_suggestion_is_the_domain_rule_and_not_a_second_copy(self) -> None:
        """Asserted against `suggest_grade` itself rather than against a literal.
        A use case that computed its own would pass a literal and disagree with
        the scheduler the moment the rule changed.
        """
        world = an_environment()
        attempt_id = a_graded_attempt(world)

        offer = an_offer_review(world)(attempt_id)

        stored = world.attempts.get(attempt_id)
        assert stored is not None
        assert offer.suggestion == suggest_grade(stored, offer.exercise)

    def test_an_exercise_never_scheduled_has_no_card(self) -> None:
        """`None` rather than a `NEW` card invented here: the repository refuses
        to manufacture one, and so does this.
        """
        world = an_environment()

        offer = an_offer_review(world)(a_graded_attempt(world))

        assert offer.card is None
        assert offer.already_reviewed is False

    def test_it_reads_nothing_and_writes_nothing(self) -> None:
        world = an_environment()
        attempt_id = a_graded_attempt(world)

        an_offer_review(world)(attempt_id)

        assert len(world.reviews) == 0
        assert world.scheduler.calls == []

    def test_it_refuses_an_attempt_that_has_no_verdict(self) -> None:
        world = an_environment()
        attempt_id = a_start_attempt(world)(KATA).attempt.id

        with pytest.raises(AttemptStateError, match="no verdict to grade"):
            an_offer_review(world)(attempt_id)

    def test_it_refuses_an_id_nothing_resolves(self) -> None:
        with pytest.raises(AttemptNotFoundError, match="no attempt with id"):
            an_offer_review(an_environment())(MISSING)

    def test_it_refuses_an_attempt_whose_exercise_has_left_the_library(self) -> None:
        world = an_environment()
        attempt_id = a_graded_attempt(world)
        world.content.forget(KATA)

        with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
            an_offer_review(world)(attempt_id)


# --- GradeReview -----------------------------------------------------------


class TestGradeReview:
    def test_it_applies_the_suggestion_when_no_grade_is_given(self) -> None:
        """The suggestion's whole delivery mechanism: one surface offering a
        single button and another offering four reach the same use case.
        """
        world = an_environment()
        attempt_id = a_graded_attempt(world)

        reviewed = a_grade_review(world)(attempt_id)

        assert world.scheduler.grades == [Grade.EASY]
        assert reviewed.grade is Grade.EASY
        assert reviewed.followed_the_suggestion is True

    def test_an_explicit_grade_overrides_it(self) -> None:
        world = an_environment()
        attempt_id = a_graded_attempt(world)

        reviewed = a_grade_review(world)(attempt_id, Grade.HARD)

        assert world.scheduler.grades == [Grade.HARD]
        assert reviewed.grade is Grade.HARD
        assert reviewed.followed_the_suggestion is False
        # The suggestion still comes back: an override is the only feedback the
        # rule will ever get, and a response that dropped it could not report one.
        assert reviewed.suggestion.grade is Grade.EASY

    def test_it_stores_the_card_the_scheduler_returned(self) -> None:
        world = an_environment()
        attempt_id = a_graded_attempt(world)

        reviewed = a_grade_review(world)(attempt_id)

        assert world.reviews.get_card(KATA) == reviewed.card
        assert reviewed.interval_days == 3

    def test_it_creates_the_card_for_an_exercise_never_scheduled(self) -> None:
        """`ReviewRepository.get_card` deliberately will not invent one -- it has
        no clock. This has one, so `ReviewCard.new` is its call to make.
        """
        world = an_environment()
        attempt_id = a_graded_attempt(world)

        a_grade_review(world)(attempt_id)

        (call,) = world.scheduler.calls
        assert call.card == ReviewCard.new(KATA, world.clock.today())
        assert call.now == world.clock.now()

    def test_it_passes_the_stored_card_on_when_there_is_one(self) -> None:
        world = an_environment()
        world.reviews.save_card(
            ReviewCard(
                exercise_id=KATA,
                due_on=world.clock.today(),
                state=CardState.REVIEW,
                interval_days=10,
                reps=4,
            )
        )

        a_grade_review(world)(a_graded_attempt(world))

        (call,) = world.scheduler.calls
        assert call.card.interval_days == 10
        assert call.card.reps == 4

    def test_a_failing_attempt_suggests_again(self) -> None:
        world = a_failing_world()
        attempt_id = a_graded_attempt(world)

        reviewed = a_grade_review(world)(attempt_id)

        assert reviewed.grade is Grade.AGAIN

    def test_one_attempt_moves_the_card_once(self) -> None:
        """A double-click, a refresh, or a tab left open. Without the guard the
        interval advances twice for one piece of evidence, and a card is replaced
        rather than versioned -- so there would be nothing to undo it from.
        """
        world = an_environment()
        attempt_id = a_graded_attempt(world)
        a_grade_review(world)(attempt_id)

        with pytest.raises(AttemptStateError, match="already been reviewed"):
            a_grade_review(world)(attempt_id)

        assert len(world.scheduler.calls) == 1

    def test_the_refusal_says_when_the_exercise_is_next_due(self) -> None:
        """The reader double-clicked Schedule; the useful thing to tell them is
        not that it failed but that it worked the first time.
        """
        world = an_environment()
        attempt_id = a_graded_attempt(world)
        reviewed = a_grade_review(world)(attempt_id)

        with pytest.raises(AttemptStateError, match=reviewed.card.due_on.isoformat()):
            a_grade_review(world)(attempt_id)

    def test_a_later_attempt_at_the_same_exercise_may_review_it_again(self) -> None:
        """The guard is per *attempt*, not per card. Practising the same exercise
        twice in a week is the normal use of the tool, and a guard on the card
        would turn the second session into an error.
        """
        world = an_environment()
        a_grade_review(world)(a_graded_attempt(world))
        world.clock.advance(timedelta(days=1))

        a_grade_review(world)(a_graded_attempt(world), Grade.HARD)

        assert world.scheduler.grades == [Grade.EASY, Grade.HARD]

    def test_it_refuses_an_attempt_that_has_no_verdict(self) -> None:
        world = an_environment()
        attempt_id = a_start_attempt(world)(KATA).attempt.id

        with pytest.raises(AttemptStateError, match="no verdict to grade"):
            a_grade_review(world)(attempt_id)

        assert len(world.reviews) == 0

    def test_it_refuses_an_id_nothing_resolves(self) -> None:
        with pytest.raises(AttemptNotFoundError, match="no attempt with id"):
            a_grade_review(an_environment())(MISSING)


# --- ReviewQueue -----------------------------------------------------------


class TestReviewQueue:
    def test_an_unpractised_library_is_entirely_due(self) -> None:
        """The state a fresh install is in, and the one where the question most
        needs answering. A queue built from the card table alone would be empty.
        """
        world = an_environment()

        queue = a_review_queue(world)()

        assert [str(row.exercise.id) for row in queue] == [str(SCENARIO), str(KATA)]
        assert all(row.is_new for row in queue)

    def test_a_scheduled_exercise_leaves_the_queue_until_it_comes_due(self) -> None:
        world = an_environment()
        a_grade_review(world)(a_graded_attempt(world))

        queue = a_review_queue(world)()

        assert [str(row.exercise.id) for row in queue] == [str(SCENARIO)]

    def test_it_comes_back_on_the_day_it_is_due(self) -> None:
        world = an_environment()
        reviewed = a_grade_review(world)(a_graded_attempt(world))
        world.clock.advance(timedelta(days=3))

        queue = a_review_queue(world)()

        assert world.clock.today() == reviewed.card.due_on
        assert [str(row.exercise.id) for row in queue] == [str(KATA), str(SCENARIO)]

    def test_due_cards_come_before_exercises_never_scheduled(self) -> None:
        """Something already learned and slipping is worth more than something
        new, which is the whole claim spaced repetition makes.
        """
        world = an_environment()
        a_grade_review(world)(a_graded_attempt(world))
        world.clock.advance(timedelta(days=30))

        queue = a_review_queue(world)()

        assert [row.is_new for row in queue] == [False, True]

    def test_the_due_half_is_longest_overdue_first(self) -> None:
        """The repository's order, not one re-derived here: `due_on` already
        guarantees it, and a second opinion about "most overdue" is a second
        place for it to be wrong.
        """
        world = an_environment()
        today = world.clock.today()
        world.reviews.save_card(_a_card(KATA, today - timedelta(days=1)))
        world.reviews.save_card(_a_card(SCENARIO, today - timedelta(days=9)))

        queue = a_review_queue(world)()

        assert [str(row.exercise.id) for row in queue] == [str(SCENARIO), str(KATA)]
        assert [row.days_overdue for row in queue] == [9, 1]

    def test_a_card_for_an_exercise_that_has_left_the_library_is_dropped(self) -> None:
        """There is nothing to practise, and the row would link somewhere that
        404s. The opposite of `OpenAttempt`, where the stranded thing is the only
        thing left to act on.
        """
        world = an_environment()
        world.reviews.save_card(_a_card(ExerciseId("katas/deleted"), date(2026, 1, 1)))

        queue = a_review_queue(world)()

        assert [str(row.exercise.id) for row in queue] == [str(SCENARIO), str(KATA)]


def _a_card(exercise_id: ExerciseId, due_on: date) -> ReviewCard:
    return ReviewCard(
        exercise_id=exercise_id,
        due_on=due_on,
        state=CardState.REVIEW,
        interval_days=5,
        reps=2,
    )


# --- the DTOs' own answers -------------------------------------------------


class TestTheRowsThemselves:
    """Two properties that are reachable in states no use case produces, and are
    worth being right in anyway, because the DTO is constructible.
    """

    def test_a_new_row_is_never_overdue(self) -> None:
        row = DueExercise(exercise=a_kata(), card=None, today=date(2026, 10, 2))

        assert row.is_new is True
        assert row.days_overdue == 0

    def test_a_row_due_today_is_not_overdue_either(self) -> None:
        today = date(2026, 10, 2)
        row = DueExercise(exercise=a_kata(), card=_a_card(KATA, today), today=today)

        assert row.days_overdue == 0

    def test_an_unfinished_attempt_counts_as_unreviewed(self) -> None:
        """A refusal nobody could clear is worse than the state it guards: the
        use cases reject an attempt with no verdict long before this is built.
        """
        world = an_environment()
        exercise = a_kata()
        attempt_id = a_start_attempt(world)(KATA).attempt.id
        attempt = world.attempts.get(attempt_id)
        assert attempt is not None

        offer = ReviewOffer(
            attempt=attempt,
            exercise=exercise,
            card=replace(
                _a_card(KATA, world.clock.today()),
                last_reviewed_at=world.clock.now(),
            ),
            suggestion=GradeSuggestion(
                grade=Grade.GOOD,
                passed=True,
                advisories=0,
                hints_used=0,
                overran=False,
            ),
        )

        assert offer.already_reviewed is False

    def test_a_card_never_reviewed_counts_as_unreviewed(self) -> None:
        """The other half: a card exists, and nothing has moved it yet. Reachable
        only if a card is stored without a review, which nothing does today --
        and which the SQLite store would happily hold.
        """
        world = an_environment()
        offer = an_offer_review(world)(a_graded_attempt(world))

        stale = replace(offer, card=_a_card(KATA, date(2026, 10, 2)))

        assert stale.already_reviewed is False
