"""The session aggregate: one person's run at one exercise.

`Attempt` is the only mutable thing in the domain, and the only place the rules
about what a solver may do are enforced.

**Why it keeps a full event log.** Storing just a final state would be cheaper
and would make replay, "where did I go wrong" feedback, and the process
assertions in PLAN.md §6.3 impossible. `command_used` reads this log, not the
repository — that is how reaching for the reflog can be rewarded and a force-push
flagged even when the resulting tree is correct.

**Why it carries an `AttemptPolicy`.** The aggregate holds an `ExerciseId`, not
an `Exercise`. Without the limits copied in at construction it could not enforce
a single one of its rules, and every limit check would leak out into the use
cases — where it will eventually be forgotten on one code path (PLAN.md §4.3,
§16).
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from datetime import datetime, timedelta  # noqa: TC003  (see the note below)
from enum import StrEnum
from typing import TYPE_CHECKING

from practice.domain.errors import (
    AttemptStateError,
    InvalidValueError,
    PolicyViolationError,
)
from practice.domain.exercise import GitScenarioSpec, Hint

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.domain.exercise import ComplexityExpectation, Exercise
    from practice.domain.ids import AttemptId, ExerciseId
    from practice.domain.verdict import Verdict

# `datetime` and `timedelta` are imported at runtime rather than behind
# TYPE_CHECKING because they are used in isinstance-free runtime positions
# (constructing a timedelta, reading tzinfo) as well as in annotations.

__all__ = [
    "Attempt",
    "AttemptEvent",
    "AttemptPolicy",
    "AttemptStatus",
    "CommandResult",
    "CommandRun",
    "ComplexityClaim",
    "HintRevealed",
    "SolutionSaved",
]


class AttemptStatus(StrEnum):
    """An attempt is active until it is submitted or abandoned (PLAN.md §8.1).

    The workspace on disk lives exactly as long as `ACTIVE`, which is what makes
    the resume-or-abandon prompt on startup and the `practice gc` definition of an
    orphan possible.
    """

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass(frozen=True, slots=True)
class CommandResult:
    """What running one command produced. Output is already capped by the sandbox."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    truncated: bool = False

    def __post_init__(self) -> None:
        if self.duration_ms < 0:
            raise InvalidValueError("duration_ms cannot be negative")

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


@dataclass(frozen=True, slots=True)
class ComplexityClaim:
    """The solver's self-reported cost, compared against but never graded by the
    exercise's expectation (PLAN.md §7).

    A value object with both axes rather than the single string §4.3 sketched: the
    thing it is compared against has two, and one string cannot disagree with an
    expectation on only one of them.
    """

    time: str
    space: str

    def __post_init__(self) -> None:
        if not self.time.strip() or not self.space.strip():
            raise InvalidValueError("a complexity claim needs both time and space")

    @staticmethod
    def _normalise(value: str) -> str:
        """Fold away the differences nobody means: case and spacing."""
        return "".join(value.split()).casefold()

    def agrees_with(self, expectation: ComplexityExpectation) -> bool:
        return self._normalise(self.time) == self._normalise(
            expectation.expected_time
        ) and self._normalise(self.space) == self._normalise(expectation.expected_space)


@dataclass(frozen=True, slots=True)
class CommandRun:
    """One command the solver ran, and what it did."""

    at: datetime
    argv: tuple[str, ...]
    result: CommandResult

    def __post_init__(self) -> None:
        if not self.argv:
            raise InvalidValueError("a command run needs an argv")

    @property
    def program(self) -> str:
        return self.argv[0]

    @property
    def command_line(self) -> str:
        """The single line the process assertions match their patterns against.

        Rebuilt from argv with `shlex.join` rather than stored as typed, so the
        string a pattern sees is normalised — one space between arguments, no
        matter how the solver spaced them.
        """
        return shlex.join(self.argv)


@dataclass(frozen=True, slots=True)
class HintRevealed:
    """`index` is the position in the policy's hint list, so the log records which
    hint was shown even if the exercise is later edited.
    """

    at: datetime
    index: int
    hint: Hint


@dataclass(frozen=True, slots=True)
class SolutionSaved:
    """A kata source snapshot. Kept in full so an attempt can be replayed."""

    at: datetime
    source: str


type AttemptEvent = CommandRun | HintRevealed | SolutionSaved


@dataclass(frozen=True, slots=True)
class AttemptPolicy:
    """Limits copied from the `Exercise` when the `Attempt` is constructed."""

    max_commands: int
    hints: tuple[Hint, ...]
    allowed_commands: frozenset[str]

    def __post_init__(self) -> None:
        if self.max_commands < 0:
            raise InvalidValueError("max_commands cannot be negative")

    @classmethod
    def for_exercise(cls, exercise: Exercise) -> AttemptPolicy:
        """Only a scenario has a command budget. Everything else gets zero.

        Not a special case so much as the honest encoding: a kata has no command
        console, so every command against one is out of policy.

        **The one place a third kind cost nothing.** Phase 14's SQL drills also
        have no console, and they fall into the same branch unchanged — because
        this was written as *scenarios have a budget* rather than as *katas do
        not*, which is the opposite of the mistake five other call sites made
        (`exercise.editable_source`). The difference is that the question here
        was always about the thing that is true of one kind, not about the thing
        that happened to be true of the other.
        """
        spec = exercise.spec
        if isinstance(spec, GitScenarioSpec):
            return cls(
                max_commands=spec.max_commands,
                hints=exercise.hints,
                allowed_commands=spec.allowed_commands,
            )
        return cls(
            max_commands=0,
            hints=exercise.hints,
            allowed_commands=frozenset(),
        )

    @property
    def hint_count(self) -> int:
        return len(self.hints)


class Attempt:
    """One run at one exercise. Mutable, and the guardian of its own lifecycle.

    Timestamps are passed in rather than read from a clock, because the domain has
    no clock — the `Clock` port is injected into the use case that drives this.
    Every timestamp must be timezone-aware and must not go backwards; a log whose
    ordering cannot be trusted is not much use for replay.
    """

    __slots__ = (
        "_declared_complexity",
        "_events",
        "_exercise_id",
        "_finished_at",
        "_id",
        "_policy",
        "_started_at",
        "_status",
        "_verdict",
    )

    def __init__(
        self,
        *,
        attempt_id: AttemptId,
        exercise_id: ExerciseId,
        policy: AttemptPolicy,
        started_at: datetime,
    ) -> None:
        _require_aware(started_at, "started_at")
        self._id = attempt_id
        self._exercise_id = exercise_id
        self._policy = policy
        self._started_at = started_at
        self._events: list[AttemptEvent] = []
        self._status = AttemptStatus.ACTIVE
        self._finished_at: datetime | None = None
        self._verdict: Verdict | None = None
        self._declared_complexity: ComplexityClaim | None = None

    # --- reconstitution -----------------------------------------------------

    # Nine parameters, and every one of them is a field of the aggregate: this is
    # the whole of an attempt's persisted state, keyword-only, so a mapper that
    # forgets one gets a type error rather than a silently defaulted field. A
    # parameter object here would be the row type the mappers already are.
    @classmethod
    def restore(  # noqa: PLR0913
        cls,
        *,
        attempt_id: AttemptId,
        exercise_id: ExerciseId,
        policy: AttemptPolicy,
        started_at: datetime,
        status: AttemptStatus,
        events: Sequence[AttemptEvent] = (),
        finished_at: datetime | None = None,
        verdict: Verdict | None = None,
        declared_complexity: ComplexityClaim | None = None,
    ) -> Attempt:
        """Rebuild a stored attempt. The repository's door, and nothing else's.

        **Restoring state is not replaying behaviour, and conflating the two is the
        mistake this exists to avoid.** The obvious alternative is to replay the log
        through the public API — construct, then `record_command` for each stored
        command, then `complete` — which reads as elegant and is wrong in two ways.
        It re-checks the *current* policy against a past attempt, so an exercise
        edited to allow fewer commands would make last week's attempts unloadable;
        and it re-runs invariants that were already satisfied when the events
        happened, which means the aggregate could refuse to load a row it had itself
        produced. An attempt is graded under the rules it was started under — that is
        the whole reason `AttemptPolicy` is copied in (PLAN.md §4.3) — and those
        rules are stored with it.

        So this bypasses the behavioural guards and enforces only what a *row* can
        be wrong about: timestamps that are naive or go backwards, and the three
        pairings between status, `finished_at` and `verdict`. A mapper bug then fails
        here, naming the field, rather than producing an attempt that claims to be
        active and finished at the same time.
        """
        attempt = cls(
            attempt_id=attempt_id,
            exercise_id=exercise_id,
            policy=policy,
            started_at=started_at,
        )

        last = started_at
        for position, event in enumerate(events):
            _require_aware(event.at, f"events[{position}].at")
            if event.at < last:
                raise InvalidValueError(
                    f"attempt {attempt_id} has events out of order: "
                    f"events[{position}] is at {event.at}, after {last}"
                )
            last = event.at

        if (status is AttemptStatus.ACTIVE) is (finished_at is not None):
            raise InvalidValueError(
                f"an attempt is active until it finishes: {status.value} with "
                f"finished_at={finished_at!r}"
            )
        if finished_at is not None:
            _require_aware(finished_at, "finished_at")
            if finished_at < last:
                raise InvalidValueError(
                    f"attempt {attempt_id} finished at {finished_at}, before its "
                    f"last event at {last}"
                )
        if (status is AttemptStatus.COMPLETED) is (verdict is None):
            raise InvalidValueError(
                f"only a completed attempt carries a verdict: {status.value} with "
                f"verdict={'a verdict' if verdict is not None else None}"
            )

        attempt._events = list(events)
        attempt._status = status
        attempt._finished_at = finished_at
        attempt._verdict = verdict
        attempt._declared_complexity = declared_complexity
        return attempt

    # --- identity and state -------------------------------------------------

    @property
    def id(self) -> AttemptId:
        return self._id

    @property
    def exercise_id(self) -> ExerciseId:
        return self._exercise_id

    @property
    def policy(self) -> AttemptPolicy:
        return self._policy

    @property
    def started_at(self) -> datetime:
        return self._started_at

    @property
    def finished_at(self) -> datetime | None:
        return self._finished_at

    @property
    def status(self) -> AttemptStatus:
        return self._status

    @property
    def is_active(self) -> bool:
        return self._status is AttemptStatus.ACTIVE

    @property
    def verdict(self) -> Verdict | None:
        return self._verdict

    @property
    def declared_complexity(self) -> ComplexityClaim | None:
        return self._declared_complexity

    # --- the event log ------------------------------------------------------

    @property
    def events(self) -> tuple[AttemptEvent, ...]:
        """A copy, so nothing outside the aggregate can append to the log."""
        return tuple(self._events)

    @property
    def commands(self) -> tuple[CommandRun, ...]:
        return tuple(event for event in self._events if isinstance(event, CommandRun))

    @property
    def command_count(self) -> int:
        return len(self.commands)

    @property
    def remaining_commands(self) -> int:
        return self._policy.max_commands - self.command_count

    @property
    def revealed_hints(self) -> tuple[HintRevealed, ...]:
        """Every hint this attempt has been shown, in the order it was shown.

        The events rather than the `Hint`s, because a page redrawing the panel
        wants the index as well as the text -- "hint 2 of 4" is the thing that
        makes a progressive reveal legible, and the index is recorded precisely so
        the log still says *which* hint was shown after the exercise is edited.

        Shaped like `commands`, and for the same reason: a template cannot filter a
        heterogeneous event log by type, and teaching it to would put a second
        opinion about the log's shape outside the aggregate.
        """
        return tuple(event for event in self._events if isinstance(event, HintRevealed))

    @property
    def hints_revealed(self) -> int:
        return len(self.revealed_hints)

    @property
    def remaining_hints(self) -> int:
        return self._policy.hint_count - self.hints_revealed

    # --- behaviour ---------------------------------------------------------

    def record_command(
        self,
        argv: Sequence[str],
        result: CommandResult,
        *,
        at: datetime,
    ) -> CommandRun:
        """Record a command that has already run.

        The allowlist is checked here as well as in the sandbox's command policy.
        That is deliberate duplication: the adapter's job is to refuse to *execute*
        a disallowed command, and this one's is to refuse to *remember* one, so a
        future execution path that forgets the check cannot quietly produce an
        attempt whose log contradicts the exercise's own rules.
        """
        self._require_active("record a command")
        self._require_forward(at)

        if not argv:
            raise InvalidValueError("cannot record an empty command")
        program = argv[0]
        if program not in self._policy.allowed_commands:
            raise PolicyViolationError(
                f"{program!r} is not allowed by this exercise; allowed: "
                f"{', '.join(sorted(self._policy.allowed_commands)) or '(none)'}"
            )
        if self.command_count >= self._policy.max_commands:
            raise PolicyViolationError(
                f"command budget exhausted: {self._policy.max_commands} commands"
            )

        event = CommandRun(at=at, argv=tuple(argv), result=result)
        self._events.append(event)
        return event

    def reveal_next_hint(self, *, at: datetime) -> Hint:
        """Reveal hints strictly in order; refuse once they run out."""
        self._require_active("reveal a hint")
        self._require_forward(at)

        index = self.hints_revealed
        if index >= self._policy.hint_count:
            raise PolicyViolationError(
                f"no hints left: this exercise has {self._policy.hint_count}"
            )

        hint = self._policy.hints[index]
        self._events.append(HintRevealed(at=at, index=index, hint=hint))
        return hint

    def save_solution(self, source: str, *, at: datetime) -> None:
        """Snapshot a kata source. Called on every save, not only on submit."""
        self._require_active("save a solution")
        self._require_forward(at)
        self._events.append(SolutionSaved(at=at, source=source))

    def declare_complexity(self, claim: ComplexityClaim) -> None:
        """Record the solver's own Big-O claim. Replaceable until submission."""
        self._require_active("declare complexity")
        self._declared_complexity = claim

    def complete(self, verdict: Verdict, *, at: datetime) -> None:
        """Submit: attach the verdict and close the attempt for good."""
        self._require_active("complete")
        self._require_forward(at)
        self._verdict = verdict
        self._finished_at = at
        self._status = AttemptStatus.COMPLETED

    def abandon(self, *, at: datetime) -> None:
        """Give up without submitting, freeing the workspace for collection."""
        self._require_active("abandon")
        self._require_forward(at)
        self._finished_at = at
        self._status = AttemptStatus.ABANDONED

    def elapsed(self, now: datetime) -> timedelta:
        """Wall-clock time spent. Frozen once the attempt finishes."""
        _require_aware(now, "now")
        end = self._finished_at if self._finished_at is not None else now
        if end < self._started_at:
            raise InvalidValueError("an attempt cannot end before it started")
        return end - self._started_at

    # --- guards ------------------------------------------------------------

    def _require_active(self, action: str) -> None:
        if self._status is not AttemptStatus.ACTIVE:
            raise AttemptStateError(
                f"cannot {action}: attempt {self._id} is {self._status.value}"
            )

    def _require_forward(self, at: datetime) -> None:
        _require_aware(at, "at")
        if at < self._last_event_at:
            raise InvalidValueError(
                f"attempt {self._id} already has an event at {self._last_event_at}; "
                f"refusing to record one at {at}"
            )

    @property
    def _last_event_at(self) -> datetime:
        if not self._events:
            return self._started_at
        return self._events[-1].at

    def __repr__(self) -> str:
        return (
            f"Attempt(id={self._id}, exercise_id={self._exercise_id}, "
            f"status={self._status.value}, events={len(self._events)})"
        )


def _require_aware(value: datetime, name: str) -> None:
    """Naive datetimes are rejected at the boundary, not normalised.

    Guessing a timezone for a timestamp that arrived without one is how an attempt
    ends up with a duration of minus seven hours.
    """
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise InvalidValueError(f"{name} must be timezone-aware")
