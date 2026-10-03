"""Review cards in SQLite. One row per exercise, and no history.

Satisfies `practice.domain.ports.ReviewRepository`, structurally (ADR 0002).

**A card is replaced, never versioned.** `ReviewCard` is a frozen dataclass and the
scheduler returns a new one, so `save_card` is an upsert on `exercise_id` and the
previous state is gone. That is a real decision rather than the obvious one: a
review *log* — every grade ever given, with the interval it produced — is what
would let the Phase 9 scheduler be evaluated against its own history rather than
only property-tested, and it is also a table nothing in the MVP reads. So it is not
here, and the `reps`/`lapses` counters the card already carries are what survives
instead. The thing to notice if that choice is revisited is that the counters are
derivable from a log and the log is not derivable from the counters.

**There is no `Scheduler` yet, and this still earns its place now.** PLAN.md §13's
rule is that a port with one implementation and no test double gets deleted;
`ReviewRepository` was declared in Phase 1 with every other protocol and had none at
all. This commit gives it two — this one and the in-memory store beside it — which
is what makes Phase 9's arithmetic something that can be tested against a repository
instead of against a dict it invents on the spot.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from practice.adapters.persistence.sqlite.mappers import card_row, to_card

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Mapping, Sequence
    from datetime import date

    from practice.adapters.persistence.sqlite.connection import Database
    from practice.domain.ids import ExerciseId
    from practice.domain.review import ReviewCard

__all__ = ["SqliteReviewRepository"]

_COLUMNS: Final = (
    "exercise_id",
    "state",
    "ease",
    "interval_days",
    "reps",
    "lapses",
    "due_on",
    "last_reviewed_at",
)

#: Everything but the key, because everything but the key is what a review moves.
_MUTABLE: Final = tuple(column for column in _COLUMNS if column != "exercise_id")

_UPSERT_CARD: Final = (
    f"INSERT INTO review_cards ({', '.join(_COLUMNS)}) "  # noqa: S608  (a literal)
    f"VALUES ({', '.join(f':{column}' for column in _COLUMNS)}) "
    f"ON CONFLICT (exercise_id) DO UPDATE SET "
    f"{', '.join(f'{column} = excluded.{column}' for column in _MUTABLE)}"
)

_SELECT_CARD: Final = "SELECT * FROM review_cards WHERE exercise_id = :exercise_id"

#: `<=`, matching `ReviewCard.is_due`: a card that came due last week and was not
#: reviewed is still due, and a queue that only showed today's would hide it.
#: Ordered oldest-first, so the longest-overdue card is the one offered next.
_SELECT_DUE: Final = (
    "SELECT * FROM review_cards WHERE due_on <= :day ORDER BY due_on, exercise_id"
)

#: The whole table. No `WHERE`, so no index helps and none is wanted: the review
#: queue has to join against the entire library anyway, and the progress page's
#: mastery counts read every card by definition.
_SELECT_ALL: Final = "SELECT * FROM review_cards ORDER BY exercise_id"


class SqliteReviewRepository:
    """Scheduling state for every exercise that has ever been graded."""

    __slots__ = ("_database",)

    def __init__(self, database: Database) -> None:
        self._database = database

    def get_card(self, exercise_id: ExerciseId) -> ReviewCard | None:
        """`None` for an exercise never attempted.

        Rather than a `NEW` card invented on the spot: `ReviewCard.new` needs
        today's date, this layer has no clock, and a repository that quietly
        manufactured domain objects would make "has this ever been reviewed?"
        unanswerable.
        """
        with self._database.connect() as connection:
            row = connection.execute(
                _SELECT_CARD, {"exercise_id": str(exercise_id)}
            ).fetchone()
        return to_card(_mapping(row)) if row is not None else None

    def save_card(self, card: ReviewCard) -> None:
        """Insert or replace. One row per exercise, no history (see the module)."""
        with self._database.connect() as connection:
            connection.execute(_UPSERT_CARD, card_row(card))

    def due_on(self, day: date) -> Sequence[ReviewCard]:
        """Every card due on or before `day`, longest-overdue first."""
        with self._database.connect() as connection:
            rows = connection.execute(_SELECT_DUE, {"day": day.isoformat()}).fetchall()
        return tuple(to_card(_mapping(row)) for row in rows)

    def cards(self) -> Sequence[ReviewCard]:
        """Every card, in exercise-id order. See the port for why both exist."""
        with self._database.connect() as connection:
            rows = connection.execute(_SELECT_ALL).fetchall()
        return tuple(to_card(_mapping(row)) for row in rows)

    def __len__(self) -> int:
        with self._database.connect() as connection:
            return int(
                connection.execute("SELECT count(*) FROM review_cards").fetchone()[0]
            )

    def __repr__(self) -> str:
        return f"SqliteReviewRepository({self._database.path})"


def _mapping(row: sqlite3.Row) -> Mapping[str, object]:
    """A `sqlite3.Row` as something the mappers can read; see `attempts.py`."""
    return {key: row[key] for key in row.keys()}  # noqa: SIM118  (Row keys need the call)
