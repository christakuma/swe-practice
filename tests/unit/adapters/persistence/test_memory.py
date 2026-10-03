"""The in-memory attempt store, and the one property that makes it useful.

Most of this file is the port's contract — save, get, miss, history. The test
that earns the file is `test_it_stores_a_snapshot_rather_than_the_aggregate`:
a store that kept the caller's object would make `save` nearly a no-op and let
every use case forget to call it, with the bug appearing only when SQLite lands
in Phase 6. These tests are the second implementation keeping the port honest
(PLAN.md §13), so they have to hold it to database semantics rather than to
whatever a dict happens to do.
"""

from __future__ import annotations

from datetime import date

from practice.adapters.persistence import (
    InMemoryAttemptRepository,
    InMemoryReviewRepository,
)
from practice.domain.attempt import Attempt, AttemptPolicy, AttemptStatus
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.review import ReviewCard
from practice.domain.verdict import CheckReport, Severity, Verdict
from tests.fakes import FakeClock, a_kata

KATA = a_kata()
OTHER = ExerciseId("katas/valid-parentheses")
TODAY = date(2026, 10, 2)


def an_attempt(number: int, exercise_id: ExerciseId | None = None) -> Attempt:
    return Attempt(
        attempt_id=AttemptId.parse(f"{number:08x}-0000-4000-8000-000000000000"),
        exercise_id=exercise_id if exercise_id is not None else KATA.id,
        policy=AttemptPolicy.for_exercise(KATA),
        started_at=FakeClock().now(),
    )


def a_verdict() -> Verdict:
    return Verdict(
        reports=(
            CheckReport(
                check_id="one",
                label="It works.",
                severity=Severity.REQUIRED,
                passed=True,
            ),
        )
    )


def test_an_attempt_can_be_saved_and_read_back() -> None:
    attempts = InMemoryAttemptRepository()
    attempt = an_attempt(1)

    attempts.save(attempt)

    stored = attempts.get(attempt.id)
    assert stored is not None
    assert stored.id == attempt.id
    assert stored.exercise_id == attempt.exercise_id
    assert stored.status is AttemptStatus.ACTIVE


def test_an_unknown_id_is_a_miss_rather_than_an_error() -> None:
    """A caller holding an id that no longer resolves — a stale URL, an attempt
    from a previous process — is a normal thing to decide about.
    """
    assert InMemoryAttemptRepository().get(an_attempt(9).id) is None


def test_saving_twice_replaces_rather_than_appends() -> None:
    """One attempt is saved at least twice: once when it starts, once graded."""
    attempts = InMemoryAttemptRepository()
    attempt = an_attempt(1)
    attempts.save(attempt)

    attempt.complete(a_verdict(), at=FakeClock().now())
    attempts.save(attempt)

    stored = attempts.get(attempt.id)
    assert stored is not None
    assert stored.status is AttemptStatus.COMPLETED
    assert len(attempts) == 1


def test_it_stores_a_snapshot_rather_than_the_aggregate() -> None:
    """The decision this adapter exists to make.

    Keeping the caller's object would mean mutating an attempt after saving it
    "persists" the change by accident — every use case would pass its test here
    and lose data against a database, where a row is only what the last `save`
    wrote.
    """
    attempts = InMemoryAttemptRepository()
    attempt = an_attempt(1)
    attempts.save(attempt)

    attempt.complete(a_verdict(), at=FakeClock().now())

    stored = attempts.get(attempt.id)
    assert stored is not None
    assert stored.status is AttemptStatus.ACTIVE, "the unsaved change leaked in"


def test_what_is_read_back_is_a_copy_too() -> None:
    """Symmetrically: mutating what `get` returned must not reach the store, or
    a read would be a back door onto the same aliasing.
    """
    attempts = InMemoryAttemptRepository()
    attempt = an_attempt(1)
    attempts.save(attempt)

    first = attempts.get(attempt.id)
    assert first is not None
    first.abandon(at=FakeClock().now())

    second = attempts.get(attempt.id)
    assert second is not None
    assert second.status is AttemptStatus.ACTIVE


def test_history_holds_only_the_attempts_at_that_exercise() -> None:
    attempts = InMemoryAttemptRepository()
    attempts.save(an_attempt(1))
    attempts.save(an_attempt(2, OTHER))
    attempts.save(an_attempt(3))

    history = attempts.history_for(KATA.id)

    assert [attempt.id.short for attempt in history] == ["00000001", "00000003"]


def test_history_for_an_exercise_nobody_attempted_is_empty() -> None:
    assert InMemoryAttemptRepository().history_for(OTHER) == ()


def test_active_holds_only_what_has_not_finished() -> None:
    """The query PLAN.md §8.1 ties the workspace lifetime to, answered here by
    filtering where the SQLite store has an index on the status.
    """
    attempts = InMemoryAttemptRepository()
    still_going = an_attempt(1)
    graded = an_attempt(2)
    graded.complete(a_verdict(), at=FakeClock().now())
    given_up = an_attempt(3)
    given_up.abandon(at=FakeClock().now())
    for attempt in (still_going, graded, given_up):
        attempts.save(attempt)

    assert [attempt.id.short for attempt in attempts.active()] == ["00000001"]


def test_active_hands_out_copies_like_every_other_read() -> None:
    """Otherwise the resume prompt would hold the store's own aggregate, and
    abandoning what it offered would mutate the row without saving it.
    """
    attempts = InMemoryAttemptRepository()
    attempts.save(an_attempt(1))

    (offered,) = attempts.active()
    offered.abandon(at=FakeClock().now())

    assert len(attempts.active()) == 1


def test_nothing_is_active_in_an_empty_store() -> None:
    assert InMemoryAttemptRepository().active() == ()


def test_it_describes_itself_by_how_much_it_holds() -> None:
    attempts = InMemoryAttemptRepository()
    attempts.save(an_attempt(1))

    assert repr(attempts) == "InMemoryAttemptRepository(1 attempts)"


class TestInMemoryReviewRepository:
    """The second implementation of `ReviewRepository`, and the one Phase 9's
    scheduler tests will use rather than opening a database to check arithmetic.
    """

    def test_a_card_comes_back_as_it_went_in(self) -> None:
        reviews = InMemoryReviewRepository()
        card = ReviewCard.new(KATA.id, TODAY)

        reviews.save_card(card)

        assert reviews.get_card(KATA.id) == card

    def test_an_exercise_never_reviewed_has_no_card(self) -> None:
        """`None`, never a card invented here: this layer has no clock, and a store
        that manufactured one would make "has this ever been reviewed?" unanswerable.
        """
        assert InMemoryReviewRepository().get_card(OTHER) is None

    def test_saving_the_same_exercise_twice_replaces_the_card(self) -> None:
        reviews = InMemoryReviewRepository()
        reviews.save_card(ReviewCard.new(KATA.id, TODAY))

        reviews.save_card(
            ReviewCard(exercise_id=KATA.id, due_on=TODAY, interval_days=15)
        )

        assert len(reviews) == 1
        stored = reviews.get_card(KATA.id)
        assert stored is not None
        assert stored.interval_days == 15

    def test_due_on_asks_the_card_rather_than_comparing_dates_itself(self) -> None:
        """So it cannot disagree with `ReviewCard.is_due` about what due means --
        the drift that stops a fake being evidence of anything.
        """
        reviews = InMemoryReviewRepository()
        reviews.save_card(ReviewCard(exercise_id=KATA.id, due_on=date(2026, 9, 28)))
        reviews.save_card(ReviewCard(exercise_id=OTHER, due_on=date(2026, 10, 9)))

        due = reviews.due_on(TODAY)

        assert [card.exercise_id for card in due] == [KATA.id]

    def test_the_due_queue_is_longest_overdue_first(self) -> None:
        reviews = InMemoryReviewRepository()
        reviews.save_card(ReviewCard(exercise_id=KATA.id, due_on=TODAY))
        reviews.save_card(ReviewCard(exercise_id=OTHER, due_on=date(2026, 9, 28)))

        assert [card.exercise_id for card in reviews.due_on(TODAY)] == [
            OTHER,
            KATA.id,
        ]

    def test_nothing_is_due_in_an_empty_store(self) -> None:
        assert InMemoryReviewRepository().due_on(TODAY) == ()

    def test_cards_returns_everything_in_exercise_id_order(self) -> None:
        """The question `due_on` cannot answer, and the reason both exist: the
        review queue has to recognise the exercises that have *no* card, which a
        method returning the due subset can never report.

        The order is asserted rather than assumed because it is explicit here and
        not the dict's -- unlike `history_for`, whose contract is insertion order.
        """
        reviews = InMemoryReviewRepository()
        reviews.save_card(ReviewCard(exercise_id=OTHER, due_on=date(2026, 12, 1)))
        reviews.save_card(ReviewCard(exercise_id=KATA.id, due_on=date(2026, 9, 28)))

        assert [card.exercise_id for card in reviews.cards()] == [KATA.id, OTHER]

    def test_an_empty_store_has_no_cards(self) -> None:
        assert InMemoryReviewRepository().cards() == ()

    def test_it_describes_itself_by_how_much_it_holds(self) -> None:
        reviews = InMemoryReviewRepository()
        reviews.save_card(ReviewCard.new(KATA.id, TODAY))

        assert repr(reviews) == "InMemoryReviewRepository(1 cards)"
