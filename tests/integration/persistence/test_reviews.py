"""`SqliteReviewRepository` against real SQLite.

Smaller than the attempt suite, and it should be: a card is one flat row with no
child table and no event log. What is left to test is the upsert, the due query's
boundary, and the thing a frozen dataclass makes easy to get wrong in the other
direction — that a float survives the trip and comes back as a number the
`ease >= 1.3` floor can be checked against.

Phase 9 added `cards()` beside `due_on`, and the two are tested together because
the only thing worth proving about them is that they *differ*: the due query cannot
report an exercise that has no card, and that exercise is the most common thing the
review queue has to offer.
"""

from __future__ import annotations

import sqlite3
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


def test_cards_returns_every_row_including_ones_not_yet_due(
    reviews: SqliteReviewRepository,
) -> None:
    """What `due_on` cannot answer. The review queue needs the set of exercises
    that have *ever* been scheduled, so it can recognise the ones that have not.
    """
    reviews.save_card(a_card(REVERT, due_on=date(2026, 9, 28)))
    reviews.save_card(a_card(TWO_SUM, due_on=date(2026, 12, 25)))

    assert [card.exercise_id for card in reviews.due_on(TODAY)] == [REVERT]
    assert [card.exercise_id for card in reviews.cards()] == [REVERT, TWO_SUM]


def test_cards_is_empty_before_anything_is_scheduled(
    reviews: SqliteReviewRepository,
) -> None:
    assert reviews.cards() == ()


# --- the columns 0002 added -------------------------------------------------


def test_a_memory_state_survives_the_round_trip(
    reviews: SqliteReviewRepository,
) -> None:
    """The two nullable REAL columns, read back as numbers the card can check.

    The same claim the `ease` round-trip makes, and it needs making again for a
    different reason: these columns are nullable, so a mapper that read them with
    the non-null reader would turn an SM-2 card into a `RowError` rather than into
    a card with no memory state.
    """
    reviews.save_card(a_card(REVERT, stability=12.5, difficulty=6.25))

    stored = reviews.get_card(REVERT)

    assert stored is not None
    assert stored.stability == 12.5
    assert stored.difficulty == 6.25
    assert stored.has_memory_state is True


def test_a_card_with_no_memory_state_comes_back_with_none(
    reviews: SqliteReviewRepository,
) -> None:
    """Which is every row a database SM-2 filled holds, and the migration's whole
    premise: 0002 backfills nothing, so NULL has to mean exactly this.
    """
    reviews.save_card(a_card(REVERT))

    stored = reviews.get_card(REVERT)

    assert stored is not None
    assert stored.has_memory_state is False


def test_switching_schedulers_overwrites_the_memory_state_in_place(
    reviews: SqliteReviewRepository,
) -> None:
    """Both directions, because a card is replaced rather than versioned.

    The upsert's column list has to carry *every* mutable column or a switch back
    to SM-2 would leave a stale stability on the row, and the next switch forward
    would adopt it as though it were current. `_MUTABLE` is derived from
    `_COLUMNS` for this reason; the test is what proves the derivation covers the
    two columns 0002 added.
    """
    reviews.save_card(a_card(REVERT))
    reviews.save_card(a_card(REVERT, stability=9.0, difficulty=4.0))

    adopted = reviews.get_card(REVERT)
    assert adopted is not None
    assert adopted.has_memory_state is True

    reviews.save_card(a_card(REVERT))

    assert len(reviews) == 1
    reverted = reviews.get_card(REVERT)
    assert reverted is not None
    assert reverted.has_memory_state is False


def test_the_schema_refuses_half_a_memory_state(database: Database) -> None:
    """The schema's half of `ReviewCard`'s pairing invariant (0002).

    Deliberate duplication, with the jobs 0001 names: the card refuses to *reach*
    the state and the schema refuses to *store* it, so a mapper that stopped
    writing one of the two columns fails on the INSERT rather than on the read
    that eventually loads it back. Written as raw SQL because there is no way to
    get here through the domain -- which is exactly the hole this closes.
    """
    database.migrate()
    columns = "exercise_id, state, ease, interval_days, reps, lapses, due_on, stability"
    with (
        pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"),
        database.connect() as connection,
    ):
        connection.execute(
            f"INSERT INTO review_cards ({columns}) "  # noqa: S608  (a literal)
            "VALUES ('katas/two-sum', 'review', 2.5, 7, 3, 0, '2026-10-02', 4.5)"
        )


def test_the_schema_refuses_a_stability_of_zero(database: Database) -> None:
    """The other CHECK 0002 adds, and the one with teeth: zero is the value that
    would divide into elapsed time on the next review.
    """
    database.migrate()
    columns = (
        "exercise_id, state, ease, interval_days, reps, lapses, due_on, "
        "stability, difficulty"
    )
    with (
        pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"),
        database.connect() as connection,
    ):
        connection.execute(
            f"INSERT INTO review_cards ({columns}) "  # noqa: S608  (a literal)
            "VALUES ('katas/two-sum', 'review', 2.5, 7, 3, 0, "
            "'2026-10-02', 0.0, 5.0)"
        )
