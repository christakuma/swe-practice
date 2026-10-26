"""A finish date from recent pace, the choices that remember it, and a track filter.

The boundaries are the point: a projection is a number people plan around, so
the cases worth pinning are the ones where a rule could quietly invent one --
too little history, a finished track, a window edge, a redone step.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from practice.adapters.persistence import InMemorySettingsRepository
from practice.application.pace import (
    MAX_DAYS,
    MIN_PASSES,
    WINDOW_DAYS,
    pace_per_day,
    project,
    read_goal,
)
from practice.application.preferences import (
    clear_goal,
    goal_for,
    reviews_enabled,
    set_goal,
    set_reviews_enabled,
)
from practice.application.tracks import filter_steps
from tests.unit.application.test_progress import finished
from tests.unit.application.test_tracks import ONE, THREE, TWO, a_walk

TODAY = date(2026, 10, 26)


def days_ago(*counts: int) -> list[date]:
    return [TODAY - timedelta(days=count) for count in counts]


# --- pace -------------------------------------------------------------------


def test_the_window_counts_today_and_stops_before_its_far_edge() -> None:
    inside = days_ago(0, WINDOW_DAYS - 1)
    outside = days_ago(WINDOW_DAYS, WINDOW_DAYS + 5)

    rate, count = pace_per_day(inside + outside, TODAY)

    assert count == 2
    assert rate == pytest.approx(2 / WINDOW_DAYS)


def test_two_passes_are_not_enough_to_project_from() -> None:
    assert MIN_PASSES == 3
    assert project(days_ago(0, 1), remaining=50, today=TODAY) is None


def test_a_finished_track_has_nothing_to_project() -> None:
    assert project(days_ago(0, 1, 2), remaining=0, today=TODAY) is None


def test_the_projection_divides_what_is_left_by_the_measured_rate() -> None:
    # 28 passes in 28 days is one a day, so 10 left is ten days out.
    passes = [TODAY - timedelta(days=n) for n in range(WINDOW_DAYS)]

    found = project(passes, remaining=10, today=TODAY)

    assert found is not None
    assert found.finish_on == TODAY + timedelta(days=10)
    assert found.per_week == pytest.approx(7)


def test_a_date_more_than_a_year_out_is_not_printed() -> None:
    found = project(days_ago(0, 1, 2), remaining=10_000, today=TODAY)

    assert found is not None
    assert found.finish_on is None


def test_a_date_at_the_edge_of_a_year_is_still_given() -> None:
    # 28 passes in the window is one a day, so `remaining` days out exactly.
    passes = [TODAY - timedelta(days=n) for n in range(WINDOW_DAYS)]

    at_the_edge = project(passes, remaining=MAX_DAYS, today=TODAY)
    past_it = project(passes, remaining=MAX_DAYS + 1, today=TODAY)

    assert at_the_edge is not None
    assert at_the_edge.finish_on == TODAY + timedelta(days=MAX_DAYS)
    assert past_it is not None
    assert past_it.finish_on is None


# --- a goal held against the days left --------------------------------------


def test_a_goal_reports_how_much_a_week_it_asks() -> None:
    reading = read_goal(TODAY + timedelta(days=14), [], remaining=10, today=TODAY)

    assert reading.days_left == 14
    assert reading.per_week_needed == pytest.approx(5)
    assert not reading.is_overdue


def test_with_no_measured_pace_a_goal_is_never_called_behind() -> None:
    reading = read_goal(TODAY + timedelta(days=1), [], remaining=500, today=TODAY)

    assert not reading.is_behind


def test_a_goal_asking_far_more_than_the_pace_is_behind() -> None:
    passes = days_ago(0, 1, 2)  # 3 in 28 days: about 0.75 a week
    reading = read_goal(TODAY + timedelta(days=7), passes, remaining=10, today=TODAY)

    assert reading.is_behind


def test_a_goal_within_the_pace_is_not_behind() -> None:
    passes = [TODAY - timedelta(days=n) for n in range(WINDOW_DAYS)]  # 7 a week
    reading = read_goal(TODAY + timedelta(days=14), passes, remaining=10, today=TODAY)

    assert not reading.is_behind


def test_a_goal_whose_day_has_passed_is_overdue_with_the_backlog_as_todays() -> None:
    reading = read_goal(TODAY - timedelta(days=3), [], remaining=4, today=TODAY)

    assert reading.is_overdue
    assert reading.days_left == 0
    assert reading.per_week_needed == pytest.approx(28)


def test_a_goal_due_today_still_has_its_day() -> None:
    reading = read_goal(TODAY, [], remaining=4, today=TODAY)

    assert not reading.is_overdue
    assert reading.days_left == 0


def test_a_goal_on_a_finished_track_is_not_overdue() -> None:
    reading = read_goal(TODAY - timedelta(days=3), [], remaining=0, today=TODAY)

    assert not reading.is_overdue


# --- first passes -----------------------------------------------------------


def test_redoing_a_step_does_not_move_its_first_pass() -> None:
    walk = a_walk(
        finished(ONE, day=date(2026, 10, 1)),
        finished(ONE, day=date(2026, 10, 20)),
        finished(TWO, day=date(2026, 10, 5), passed=False),
    )

    assert walk.first_pass_days == (date(2026, 10, 1),)


def test_the_earliest_pass_wins_whatever_order_attempts_arrive_in() -> None:
    walk = a_walk(
        finished(ONE, day=date(2026, 10, 20)),
        finished(ONE, day=date(2026, 10, 1)),
    )

    assert walk.first_pass_days == (date(2026, 10, 1),)


# --- preferences ------------------------------------------------------------


def test_review_scheduling_is_on_until_someone_turns_it_off() -> None:
    settings = InMemorySettingsRepository()
    assert reviews_enabled(settings)

    set_reviews_enabled(settings, enabled=False)
    assert not reviews_enabled(settings)

    set_reviews_enabled(settings, enabled=True)
    assert reviews_enabled(settings)


def test_a_goal_round_trips_per_track_and_clears() -> None:
    settings = InMemorySettingsRepository()
    assert goal_for(settings, "blind-75") is None

    set_goal(settings, "blind-75", date(2026, 12, 31))

    assert goal_for(settings, "blind-75") == date(2026, 12, 31)
    assert goal_for(settings, "systems") is None
    clear_goal(settings, "blind-75")
    assert goal_for(settings, "blind-75") is None


def test_an_unreadable_stored_goal_is_no_goal() -> None:
    settings = InMemorySettingsRepository()
    settings.set("goal:blind-75", "next tuesday")

    assert goal_for(settings, "blind-75") is None


# --- the track filter -------------------------------------------------------


def test_a_search_keeps_the_tracks_own_numbers() -> None:
    walk = a_walk()

    kept = filter_steps(walk, "  THREE ")

    assert [(step.number, step.exercise.id) for step in kept] == [(3, THREE.id)]


def test_a_search_matches_a_tag() -> None:
    walk = a_walk()
    tag = next(iter(ONE.tags))

    assert any(step.exercise.id == ONE.id for step in filter_steps(walk, tag))


def test_done_and_not_done_split_the_track() -> None:
    walk = a_walk(finished(TWO))

    assert [s.number for s in filter_steps(walk, show="done")] == [2]
    assert [s.number for s in filter_steps(walk, show="todo")] == [1, 3, 4]


def test_an_unknown_show_value_means_all() -> None:
    walk = a_walk(finished(TWO))

    assert len(filter_steps(walk, show="whatever")) == walk.total


def test_a_search_with_no_match_is_empty() -> None:
    assert filter_steps(a_walk(), "zzzzzz") == ()
