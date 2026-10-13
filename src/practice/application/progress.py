"""Reading a history: the streak, mastery by tag, and a window of activity.

A view model, like `application/graph.py` and for the same reasons. Nothing here
asks a port anything — it takes the attempts, the cards and the library a use
case has already fetched and decides what they add up to — which makes it pure,
puts it inside the coverage gate, and keeps the arithmetic out of a route.

**It is not `domain/`, and the line is the same one `graph.py` draws.** A streak
is not a rule the product can be wrong about in the way an interval is: nothing
is graded by it and nothing refuses to exist because of it. It is what a page
says about you.

Three readings, and each of them is a decision rather than a sum.

**The streak does not break until a day is missed and over.** Counted back from
today when today has activity and from yesterday when it does not, so someone who
practised last night and has not started yet this morning still has their streak
— the alternative resets it at midnight and restores it that evening, which is a
counter nobody would trust. Two idle days is a break.

**Mastery is per tag and not per exercise**, because the question a solver has is
*what am I bad at*, and "you failed `git/recover-a-lost-commit`" is something they
already knew. Tags are what generalise. An attempt at an exercise carrying three
tags counts once against each, so these are per-tag rates and not a partition —
the honest shape, since the tags overlap.

**Weakness is pass rate first and lapses second.** Pass rate alone misses the
exercise that passes every time *after* you have forgotten it twice; lapses alone
miss the one you have never got right. A tag that has never been failed or lapsed
is not offered as weak at all, because a dashboard listing a perfect tag under
"weakest" teaches you to ignore that panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from practice.domain.attempt import Attempt
    from practice.domain.exercise import Exercise
    from practice.domain.ids import ExerciseId, Tag
    from practice.domain.review import ReviewCard

__all__ = [
    "WEAKEST_LIMIT",
    "WINDOW_DAYS",
    "DayActivity",
    "Progress",
    "TagMastery",
    "summarise",
]

#: How far back the activity chart looks. Four weeks and change: long enough that
#: a habit is visible, short enough that one bar is a readable width — which is
#: the constraint a hand-rolled SVG in a panel actually has.
WINDOW_DAYS: Final = 30

#: How many tags the "weakest" summary offers. Three, because it is a prompt and
#: not a report; the whole table is on `/progress` for anyone who wants it.
WEAKEST_LIMIT: Final = 3


@dataclass(frozen=True, slots=True)
class _Graded:
    """One finished attempt, with the two optional fields already resolved.

    An internal narrowing rather than a public type. `Attempt.verdict` and
    `finished_at` are `| None` because an attempt spends most of its life without
    them, and threading that through four functions means four places that could
    answer differently — or, worse, one `assert` per place, each of them a second
    claim that can drift from the filter.
    """

    attempt: Attempt
    finished_at: datetime
    passed: bool

    @property
    def day(self) -> date:
        return self.finished_at.date()

    @property
    def exercise_id(self) -> ExerciseId:
        return self.attempt.exercise_id


@dataclass(frozen=True, slots=True)
class TagMastery:
    """One tag, and how the attempts carrying it went."""

    tag: Tag
    attempted: int
    passed: int
    lapses: int

    @property
    def failed(self) -> int:
        return self.attempted - self.passed

    @property
    def pass_rate(self) -> float:
        """Zero for a tag never attempted, which a summary cannot produce and a
        test can. Nought out of nought is zero rather than undefined because the
        only consumer is the length of a bar.
        """
        return self.passed / self.attempted if self.attempted else 0.0

    @property
    def is_weak(self) -> bool:
        """Something has gone wrong with this tag at least once.

        The filter on the "weakest" list, so a library you have never failed
        reports nothing weak rather than reporting your best tag as your worst.
        """
        return self.failed > 0 or self.lapses > 0


@dataclass(frozen=True, slots=True)
class DayActivity:
    """One calendar day of the window. Present even when nothing happened.

    A contiguous series rather than only the days with attempts, because the gaps
    are the information: a chart drawn from seven rows spread over a month looks
    identical to one drawn from seven consecutive days, and those are opposite
    facts about a habit.
    """

    day: date
    attempts: int
    passed: int

    @property
    def is_idle(self) -> bool:
        return self.attempts == 0


@dataclass(frozen=True, slots=True)
class Progress:
    """Everything the dashboard and the progress page read, from one pass.

    The counts are fields rather than properties over `attempts`, which is the
    opposite of the rule `Verdict.outcome` follows and is right here for the
    opposite reason: a verdict's outcome is an invariant that must not be
    storable wrongly, and this whole object *is* a derivation. Recomputing a
    count from a list the summary has already walked would be a second walk with
    a second chance to disagree with the first.
    """

    attempts: tuple[Attempt, ...]
    passed: int
    tags: tuple[TagMastery, ...]
    days: tuple[DayActivity, ...]
    streak_days: int
    scheduled: int
    #: What to call each exercise in `attempts`, for the ones the library still
    #: holds. **A name per id and not an exercise per attempt**: an attempt
    #: whose exercise has left still counts, and pairing them would have meant
    #: dropping it or inventing one -- so it is simply absent here and a page
    #: falls back to the id. Here rather than joined by the page, because the
    #: use case has already made the join the hard way (a variant is never in
    #: the listing, ADR 0028), and a route that made it again was the second
    #: copy of that lookup with a second chance to forget the variants.
    titles: Mapping[ExerciseId, str]

    @property
    def total(self) -> int:
        return len(self.attempts)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def weakest(self) -> tuple[TagMastery, ...]:
        """The few tags worth being told about, worst first. May be empty."""
        return tuple(row for row in self.tags if row.is_weak)[:WEAKEST_LIMIT]

    @property
    def busiest_day(self) -> int:
        """The tallest bar in the window, which is the activity chart's scale.

        Here rather than in the renderer, so two charts drawn from one summary
        cannot scale differently and the empty case is answered once.
        """
        return max((day.attempts for day in self.days), default=0)


def summarise(
    *,
    attempts: Sequence[Attempt],
    exercises: Mapping[ExerciseId, Exercise],
    cards: Sequence[ReviewCard],
    today: date,
    window_days: int = WINDOW_DAYS,
) -> Progress:
    """Read a history. Newest attempt first, which is the order a page shows them.

    **An attempt without both a verdict and an end is skipped**, and that is not
    defensive tidiness about a repository already promising only completed ones:
    the fields are optional on the aggregate, and a summary that trusted its
    caller would be one import away from counting a live attempt as a failure.

    **An attempt whose exercise has left the library still counts.** It happened,
    so it belongs in the totals and the streak; what it cannot contribute is tags,
    because the thing that carried them is gone. Dropping it outright would let a
    deleted exercise retroactively shorten a streak somebody earned.
    """
    graded = _graded(attempts)
    lapses = {card.exercise_id: card.lapses for card in cards}
    return Progress(
        attempts=tuple(row.attempt for row in graded),
        passed=sum(1 for row in graded if row.passed),
        tags=_mastery(graded, exercises, lapses),
        days=_window(graded, today, window_days),
        streak_days=_streak({row.day for row in graded}, today),
        scheduled=len(cards),
        titles={
            row.exercise_id: exercises[row.exercise_id].title
            for row in graded
            if row.exercise_id in exercises
        },
    )


def _graded(attempts: Iterable[Attempt]) -> tuple[_Graded, ...]:
    """The finished attempts, newest first, with their optional fields resolved."""
    rows = [
        _Graded(
            attempt=attempt,
            finished_at=attempt.finished_at,
            passed=attempt.verdict.passed,
        )
        for attempt in attempts
        if attempt.finished_at is not None and attempt.verdict is not None
    ]
    rows.sort(key=lambda row: row.finished_at, reverse=True)
    return tuple(rows)


def _mastery(
    graded: Iterable[_Graded],
    exercises: Mapping[ExerciseId, Exercise],
    lapses: Mapping[ExerciseId, int],
) -> tuple[TagMastery, ...]:
    """Per-tag counts, worst first.

    Sorted by pass rate, then by the evidence behind it, then by name. The second
    key matters more than it looks: one failure out of one and nine out of ten are
    both 0%, they are not the same problem, and the tag with the evidence is the
    one worth offering.
    """
    attempted: dict[Tag, int] = {}
    passed: dict[Tag, int] = {}
    lapsed: dict[Tag, int] = {}
    counted: set[tuple[Tag, ExerciseId]] = set()
    for row in graded:
        exercise = exercises.get(row.exercise_id)
        if exercise is None:
            continue
        for tag in exercise.tags:
            attempted[tag] = attempted.get(tag, 0) + 1
            passed[tag] = passed.get(tag, 0) + (1 if row.passed else 0)
            # Lapses live on the card, which is per exercise, so they are added
            # once per (tag, exercise) and not once per attempt -- otherwise
            # practising the same exercise twice would double a count that
            # nothing changed.
            if (tag, exercise.id) not in counted:
                counted.add((tag, exercise.id))
                lapsed[tag] = lapsed.get(tag, 0) + lapses.get(exercise.id, 0)

    mastery = [
        TagMastery(
            tag=tag,
            attempted=count,
            passed=passed.get(tag, 0),
            lapses=lapsed.get(tag, 0),
        )
        for tag, count in attempted.items()
    ]
    mastery.sort(key=lambda row: (row.pass_rate, -row.attempted, row.tag))
    return tuple(mastery)


def _window(
    graded: Iterable[_Graded], today: date, window_days: int
) -> tuple[DayActivity, ...]:
    """`window_days` contiguous days ending today, oldest first.

    Oldest first because that is the direction a chart reads, and a renderer
    should not have to reverse a sequence to draw it the only way it can be drawn.
    An attempt finished *after* today — a clock that moved backwards, a row
    restored from a machine in another timezone — falls outside the window and is
    simply not drawn, rather than widening it.
    """
    done: dict[date, int] = {}
    won: dict[date, int] = {}
    for row in graded:
        done[row.day] = done.get(row.day, 0) + 1
        won[row.day] = won.get(row.day, 0) + (1 if row.passed else 0)

    start = today - timedelta(days=window_days - 1)
    days = [start + timedelta(days=offset) for offset in range(window_days)]
    return tuple(
        DayActivity(day=day, attempts=done.get(day, 0), passed=won.get(day, 0))
        for day in days
    )


def _streak(active: set[date], today: date) -> int:
    """Consecutive days of practice ending today, or ending yesterday.

    See the module docstring: a streak that reset at midnight and came back that
    evening is a counter nobody would trust, so today counts only if it has
    activity and is otherwise skipped rather than ending the count.
    """
    cursor = today if today in active else today - timedelta(days=1)
    length = 0
    while cursor in active:
        length += 1
        cursor -= timedelta(days=1)
    return length
