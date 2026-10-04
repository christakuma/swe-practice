"""The review card. Scheduling arithmetic arrives with the scheduler in Phase 9;
what is testable now is the card's own invariants.

Phase 13 added two of them, and they are the only invariants here that exist to
protect one scheduler from another's state: `stability` and `difficulty` are
FSRS's, SM-2 never writes either, and a card holding exactly one of the pair is
not a card either of them can read.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any

import pytest

from practice.domain.errors import InvalidValueError
from practice.domain.ids import ExerciseId
from practice.domain.review import (
    DEFAULT_EASE,
    MAXIMUM_DIFFICULTY,
    MINIMUM_DIFFICULTY,
    MINIMUM_EASE,
    CardState,
    Grade,
    ReviewCard,
)

TODAY = date(2026, 9, 30)
_CARD = ReviewCard.new(ExerciseId("katas/two-sum"), TODAY)


def a_card(**overrides: Any) -> ReviewCard:
    return replace(_CARD, **overrides)


def test_a_new_card_is_due_immediately_with_the_default_ease() -> None:
    card = ReviewCard.new(ExerciseId("katas/two-sum"), TODAY)

    assert card.state is CardState.NEW
    assert card.ease == DEFAULT_EASE
    assert card.interval_days == 0
    assert card.reps == 0
    assert card.last_reviewed_at is None
    assert card.is_due(TODAY) is True


def test_a_card_due_tomorrow_is_not_due_today() -> None:
    assert a_card(due_on=date(2026, 10, 1)).is_due(TODAY) is False


def test_an_overdue_card_is_still_due() -> None:
    assert a_card(due_on=date(2026, 9, 1)).is_due(TODAY) is True


def test_ease_may_sit_exactly_on_the_floor() -> None:
    assert a_card(ease=MINIMUM_EASE).ease == MINIMUM_EASE


def test_ease_below_the_floor_is_refused_by_the_card_itself() -> None:
    """The Phase 9 property test asserts ease never drops below 1.3. An invariant
    that only holds while one function is the sole writer is not an invariant.
    """
    with pytest.raises(InvalidValueError, match=r"1\.3"):
        a_card(ease=1.29)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [("interval_days", -1), ("reps", -1), ("lapses", -1)],
)
def test_counters_cannot_go_negative(field_name: str, value: int) -> None:
    with pytest.raises(InvalidValueError):
        a_card(**{field_name: value})


def test_last_reviewed_at_must_be_timezone_aware() -> None:
    with pytest.raises(InvalidValueError, match="timezone-aware"):
        a_card(last_reviewed_at=datetime(2026, 9, 30, 12, 0))  # noqa: DTZ001


def test_an_aware_last_reviewed_at_is_accepted() -> None:
    reviewed = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)

    assert a_card(last_reviewed_at=reviewed).last_reviewed_at == reviewed


def test_grades_are_the_four_sm2_buckets() -> None:
    assert [grade.value for grade in Grade] == ["again", "hard", "good", "easy"]


# --- the FSRS memory state Phase 13 added ----------------------------------


def test_a_card_has_no_memory_state_until_an_fsrs_scheduler_writes_one() -> None:
    """The default, and the state every card in a database SM-2 filled is in.

    `None` rather than a seeded stability, because a stability invented for a
    card with three SM-2 reviews behind it would be a fabricated memory model
    dressed as a migration (`0002_fsrs_memory_state.sql`).
    """
    card = ReviewCard.new(ExerciseId("katas/two-sum"), TODAY)

    assert card.stability is None
    assert card.difficulty is None
    assert card.has_memory_state is False


def test_a_card_with_both_halves_has_a_memory_state() -> None:
    assert a_card(stability=4.5, difficulty=5.0).has_memory_state is True


@pytest.mark.parametrize("stability", [0.0, -1.0])
def test_stability_must_be_positive(stability: float) -> None:
    """Strictly positive, and zero is the case worth naming: stability divides
    into elapsed time in FSRS's retrievability curve, so a stored zero is not a
    slightly wrong card but a `ZeroDivisionError` in the next review.
    """
    with pytest.raises(InvalidValueError, match="stability must be positive"):
        a_card(stability=stability, difficulty=5.0)


@pytest.mark.parametrize("difficulty", [0.99, 10.01])
def test_difficulty_must_be_on_the_fsrs_scale(difficulty: float) -> None:
    with pytest.raises(InvalidValueError, match="difficulty must be between"):
        a_card(stability=4.5, difficulty=difficulty)


@pytest.mark.parametrize("difficulty", [MINIMUM_DIFFICULTY, MAXIMUM_DIFFICULTY])
def test_the_ends_of_the_difficulty_scale_are_inclusive(difficulty: float) -> None:
    """Both ends are reachable: FSRS clamps to them rather than approaching them,
    so a card pinned at 1 or at 10 is the normal output of the arithmetic.
    """
    assert a_card(stability=4.5, difficulty=difficulty).difficulty == difficulty


@pytest.mark.parametrize(
    ("stability", "difficulty"),
    [(4.5, None), (None, 5.0)],
)
def test_half_a_memory_state_is_refused(
    stability: float | None, difficulty: float | None
) -> None:
    """Which is a different failure from having none, and has to read as one.

    No memory state is the ordinary case. *Half* of one is a mapper that dropped
    a column or a migration that added one, and `has_memory_state` reads a single
    field -- so without this refusal that property would be answering for a card
    it cannot actually describe.
    """
    with pytest.raises(InvalidValueError, match="set together or not at all"):
        a_card(stability=stability, difficulty=difficulty)
