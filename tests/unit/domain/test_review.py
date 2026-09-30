"""The review card. Scheduling arithmetic arrives with the scheduler in Phase 9;
what is testable now is the card's own invariants.
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
