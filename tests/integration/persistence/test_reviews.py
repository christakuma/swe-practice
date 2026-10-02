"""`SqliteReviewRepository` against real SQLite.

Smaller than the attempt suite, and it should be: a card is one flat row with no
child table and no event log. What is left to test is the upsert, the due query's
boundary, and the thing a frozen dataclass makes easy to get wrong in the other
direction — that a float survives the trip and comes back as a number the
`ease >= 1.3` floor can be checked against.

The scheduler that moves a card arrives in Phase 9. This is the table it will move
cards in, and the second implementation that stops `ReviewRepository` being a port
with nothing behind it (PLAN.md §13).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import pytest

from practice.adapters.persistence.sqlite import Database, SqliteReviewRepository
from practice.domain.errors import InvalidValueError
from practice.domain.ids import ExerciseId
from practice.domain.review import CardState, ReviewCard

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.ports import ReviewRepository

REVERT = ExerciseId("git/revert-a-pushed-commit")
TWO_SUM = ExerciseId("katas/two-sum")
TODAY = date(2026, 10, 2)


def a_card(exercise_id: ExerciseId = REVERT, **overrides: object) -> ReviewCard:
    fields: dict[str, object] = {
        "exercise_id": exercise_id,
        "due_on": TODAY,
        "state": CardState.REVIEW,
        "ease": 2.35,
        "interval_days": 6,
        "reps": 4,
        "lapses": 1,
        "last_reviewed_at": datetime(2026, 9, 26, 18, 30, tzinfo=UTC),
    }
    fields.update(overrides)
    return ReviewCard(**fields)  # type: ignore[arg-type]


@pytest.fixture
def database(tmp_path: Path) -> Database:
    return Database(tmp_path / "practice.db")


@pytest.fixture
def reviews(database: Database) -> SqliteReviewRepository:
    return SqliteReviewRepository(database)


# --- the port ---------------------------------------------------------------


def test_it_satisfies_the_review_repository_port(database: Database) -> None:
    """The annotation is the assertion. Before this commit the port had no
    implementation at all, which under §13 is a port that should have been deleted.
    """
    repository: ReviewRepository = SqliteReviewRepository(database)

    repository.save_card(a_card())

    assert repository.get_card(REVERT) is not None
    assert len(repository.due_on(TODAY)) == 1


# --- saving and loading ----------------------------------------------------


def test_a_card_comes_back_as_it_went_in(reviews: SqliteReviewRepository) -> None:
    card = a_card()

    reviews.save_card(card)

    assert reviews.get_card(REVERT) == card


def test_an_exercise_never_reviewed_has_no_card(
    reviews: SqliteReviewRepository,
) -> None:
    """`None`, not a `NEW` card invented here: `ReviewCard.new` needs today's date,
    this layer has no clock, and a repository that manufactured domain objects
    would make "has this ever been reviewed?" unanswerable.
    """
    assert reviews.get_card(TWO_SUM) is None


def test_saving_the_same_exercise_twice_replaces_the_card(
    reviews: SqliteReviewRepository,
) -> None:
    """A card is replaced, never versioned: the scheduler returns a new one and the
    previous state is gone. One row per exercise, so this must not accumulate.
    """
    reviews.save_card(a_card(interval_days=6, reps=4))

    reviews.save_card(a_card(interval_days=15, reps=5, due_on=date(2026, 10, 17)))

    assert len(reviews) == 1
    stored = reviews.get_card(REVERT)
    assert stored is not None
    assert stored.interval_days == 15
    assert stored.due_on == date(2026, 10, 17)


def test_a_card_that_has_never_been_reviewed_keeps_its_null(
    reviews: SqliteReviewRepository,
) -> None:
    """A `NEW` card is due immediately and has no `last_reviewed_at`, which is the
    only nullable column here and therefore the one worth a test of its own.
    """
    reviews.save_card(ReviewCard.new(TWO_SUM, TODAY))

    stored = reviews.get_card(TWO_SUM)

    assert stored is not None
    assert stored.last_reviewed_at is None
    assert stored.state is CardState.NEW
    assert stored.reps == 0


def test_the_ease_survives_as_a_number(reviews: SqliteReviewRepository) -> None:
    """A REAL column, and the floor is re-checked on the way back in. An `ease`
    stored as text would come back as a string and fail the comparison in
    `ReviewCard.__post_init__` rather than silently comparing wrongly.
    """
    reviews.save_card(a_card(ease=1.3))

    stored = reviews.get_card(REVERT)

    assert stored is not None
    assert stored.ease == pytest.approx(1.3)


def test_an_ease_stored_below_the_floor_is_refused_on_the_way_back(
    reviews: SqliteReviewRepository, database: Database
) -> None:
    """The reason the floor is on `ReviewCard` and not only inside the scheduler.
    The schema refuses to *store* it and the dataclass refuses to *be* it, so this
    has to go behind the repository's back to prove the second half.
    """
    reviews.save_card(a_card())
    with database.connect() as connection:
        connection.execute("PRAGMA ignore_check_constraints = ON")
        connection.execute("UPDATE review_cards SET ease = 0.5")

    with pytest.raises(InvalidValueError, match=r"1\.3"):
        reviews.get_card(REVERT)


# --- the due queue ---------------------------------------------------------


def test_due_on_includes_overdue_cards_longest_overdue_first(
    reviews: SqliteReviewRepository,
) -> None:
    """`<=`, matching `ReviewCard.is_due`: a card that came due last week and was
    not reviewed is still due, and a queue that only showed today's would hide it.
    """
    reviews.save_card(a_card(REVERT, due_on=date(2026, 9, 28)))
    reviews.save_card(a_card(TWO_SUM, due_on=TODAY))
    reviews.save_card(
        a_card(ExerciseId("katas/valid-parentheses"), due_on=date(2026, 10, 9))
    )

    due = reviews.due_on(TODAY)

    assert [str(card.exercise_id) for card in due] == [
        "git/revert-a-pushed-commit",
        "katas/two-sum",
    ]


def test_nothing_is_due_on_a_day_before_every_card(
    reviews: SqliteReviewRepository,
) -> None:
    reviews.save_card(a_card(due_on=date(2026, 10, 9)))

    assert reviews.due_on(TODAY) == ()


def test_the_due_queue_is_empty_on_a_fresh_database(
    reviews: SqliteReviewRepository,
) -> None:
    assert reviews.due_on(TODAY) == ()


def test_the_repository_describes_which_database_it_is_over(
    database: Database,
) -> None:
    assert str(database.path) in repr(SqliteReviewRepository(database))
