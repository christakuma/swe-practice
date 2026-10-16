"""Domain objects to rows, and rows back to domain objects. No SQL in here.

The half of persistence that is easy to get subtly wrong, kept in pure functions
over `Mapping`s so it can be unit-tested in milliseconds against no database at
all. What is left in the repositories is SQL, which is tested against real SQLite
because nothing else can confirm it.

**Explicit, both directions, by hand.** Every column is named in `attempt_row`
and read in `to_attempt`, which is the cost of not having an ORM and also the
thing being bought (ADR 0006): a schema change that this file does not account
for fails here, by name, instead of being guessed at by a mapping layer.

**The round trip is the contract.** `to_attempt(attempt_row(a), event_rows(a))`
must equal `a` for every attempt the aggregate can reach, including a finished one
with a verdict, a declared complexity and all three kinds of event. That property
is what `tests/unit/adapters/persistence/test_mappers.py` asserts, and it is
asserted rather than assumed because the failure mode of a mapper is silent: a
field nobody reads back is a field that persists as `None` for a year.

**Every value is re-validated on the way in.** `ExerciseId`, `AttemptId`, `Sha`
and the enums all validate on construction, so a row that has been corrupted —
by hand, by a half-written migration, by a future bug — fails at this boundary
with a message about the field rather than three layers up as something
unexplainable. A row that is structurally wrong raises `RowError`.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import TYPE_CHECKING, Final

from practice.domain.attempt import (
    Attempt,
    AttemptMode,
    AttemptPolicy,
    AttemptStatus,
    CommandResult,
    CommandRun,
    ComplexityClaim,
    HintRevealed,
    SolutionSaved,
    SubmissionFailed,
)
from practice.domain.exercise import Hint
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.review import CardState, ReviewCard
from practice.domain.verdict import CheckReport, Severity, Verdict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.domain.attempt import AttemptEvent

__all__ = [
    "COMMAND",
    "HINT",
    "SOLUTION",
    "RowError",
    "attempt_row",
    "card_row",
    "event_rows",
    "to_attempt",
    "to_card",
]

#: `attempt_events.kind`. Literals rather than the event class names,
#: because the stored value is schema — it is in a CHECK constraint — and
#: renaming a dataclass must not require a migration.
COMMAND: Final = "command"
HINT: Final = "hint"
SOLUTION: Final = "solution"
#: The fourth, from 0005: a submission that failed and left the attempt open.
SUBMISSION: Final = "submission"


class RowError(ValueError):
    """A row is not the shape this mapper can read.

    A missing column, a payload that is not JSON, an event `kind` nothing
    handles. Separate from `InvalidValueError`, which is what a *value* in an
    otherwise well-formed row raises — the distinction is between "this is not a
    row" and "this row holds something impossible", and the first one usually
    means the schema and this file have drifted apart.

    A `ValueError`, like every other refusal at a boundary in this project, so a
    caller that only wants to report the failure does not have to import it.
    """


# --- attempts: domain -> row ------------------------------------------------


def attempt_row(attempt: Attempt) -> dict[str, object]:
    """One row of `attempts`, keyed by column name.

    Keyed by name rather than positional, so the repository binds `:started_at`
    and a column added in the middle of the table by a later migration cannot
    silently shift what is written where.
    """
    claim = attempt.declared_complexity
    return {
        "id": str(attempt.id),
        "exercise_id": str(attempt.exercise_id),
        "status": attempt.status.value,
        "started_at": attempt.started_at.isoformat(),
        "finished_at": _isoformat(attempt.finished_at),
        "max_commands": attempt.policy.max_commands,
        # Sorted, so two attempts under the same policy produce byte-identical
        # rows. A set's iteration order is stable within a process and not
        # across them, which would otherwise make a stored row depend on which
        # process wrote it.
        "allowed_commands": _dump(sorted(attempt.policy.allowed_commands)),
        "hints": _dump([hint.text for hint in attempt.policy.hints]),
        # The two columns 0003 added, and the second place Phase 15 cost
        # anything. ADR 0008 predicted this shape for FSRS and it holds for a
        # mode too: a new field on a stored aggregate has to be named where
        # rows are built, however little the rest of the stack notices.
        "mode": attempt.policy.mode.value,
        "deadline_seconds": attempt.policy.deadline_seconds,
        "declared_time": claim.time if claim is not None else None,
        "declared_space": claim.space if claim is not None else None,
        "verdict": (
            _dump(_verdict_payload(attempt.verdict))
            if attempt.verdict is not None
            else None
        ),
    }


def event_rows(attempt: Attempt) -> tuple[dict[str, object], ...]:
    """One row of `attempt_events` per event, in log order.

    `position` is the index in the log rather than a timestamp, because `Attempt`
    requires timestamps to be non-decreasing and not strictly increasing: two
    commands run inside the same clock tick are a normal thing, and the order
    they were appended in is what replay depends on.
    """
    return tuple(
        {
            "attempt_id": str(attempt.id),
            "position": position,
            "at": event.at.isoformat(),
            "kind": _kind_of(event),
            "payload": _dump(_event_payload(event)),
        }
        for position, event in enumerate(attempt.events)
    )


def _kind_of(event: AttemptEvent) -> str:
    match event:
        case CommandRun():
            return COMMAND
        case HintRevealed():
            return HINT
        case SolutionSaved():
            return SOLUTION
        case SubmissionFailed():
            return SUBMISSION


def _event_payload(event: AttemptEvent) -> dict[str, object]:
    """Everything about an event except `at`, which is a column of its own.

    `at` is promoted out of the payload because it is the only field any query
    would ever filter or order by; the rest is loaded whole with its attempt and
    never queried by its parts, which is the line this schema draws between a
    column and JSON.
    """
    match event:
        case CommandRun():
            result = event.result
            return {
                "argv": list(event.argv),
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_ms": result.duration_ms,
                "truncated": result.truncated,
            }
        case HintRevealed():
            # The text as well as the index, so the log records *which* hint was
            # shown even if the exercise is later edited (PLAN.md §4.3).
            return {"index": event.index, "text": event.hint.text}
        case SolutionSaved():
            return {"source": event.source}
        case SubmissionFailed():
            # The same shape the `verdict` column holds, nested under a key so
            # the payload stays an object like every other kind's.
            return {"verdict": _verdict_payload(event.verdict)}


def _verdict_payload(verdict: Verdict) -> list[dict[str, object]]:
    """The reports, in the order the exercise declared its checks.

    A list rather than an object keyed by `check_id`: `Verdict` already refuses
    duplicate ids, and order is part of what a verdict *is* — two runs of the
    same solution have to read the same way down the page.
    """
    return [
        {
            "check_id": report.check_id,
            "label": report.label,
            "severity": report.severity.value,
            "passed": report.passed,
            "expected": report.expected,
            "actual": report.actual,
            "explanation": report.explanation,
        }
        for report in verdict.reports
    ]


# --- attempts: row -> domain ------------------------------------------------


def to_attempt(
    row: Mapping[str, object], events: Sequence[Mapping[str, object]]
) -> Attempt:
    """Rebuild one attempt from its row and its event rows, in log order.

    The events are taken in the order given rather than re-sorted by `position`:
    ordering is the repository's query's job, and silently re-sorting here would
    hide a missing `ORDER BY` that a different caller would then hit.
    """
    verdict = _required(row, "verdict", optional=True)
    status = AttemptStatus(_text(row, "status"))
    return Attempt.restore(
        attempt_id=AttemptId.parse(_text(row, "id")),
        exercise_id=ExerciseId(_text(row, "exercise_id")),
        policy=AttemptPolicy(
            max_commands=_integer(row, "max_commands"),
            hints=tuple(Hint(text) for text in _strings(row, "hints")),
            allowed_commands=frozenset(_strings(row, "allowed_commands")),
            mode=AttemptMode(_text(row, "mode")),
            deadline_seconds=_optional_integer(row, "deadline_seconds"),
        ),
        started_at=_timestamp(row, "started_at"),
        status=status,
        events=tuple(_to_event(event) for event in events),
        finished_at=_optional_timestamp(row, "finished_at"),
        verdict=_to_verdict(verdict) if verdict is not None else None,
        declared_complexity=_to_claim(row),
    )


def _to_event(row: Mapping[str, object]) -> AttemptEvent:
    at = _timestamp(row, "at")
    kind = _text(row, "kind")
    payload = _payload(row)

    if kind == COMMAND:
        return CommandRun(
            at=at,
            argv=tuple(_payload_strings(payload, "argv")),
            result=CommandResult(
                exit_code=_payload_int(payload, "exit_code"),
                stdout=_payload_text(payload, "stdout"),
                stderr=_payload_text(payload, "stderr"),
                duration_ms=_payload_int(payload, "duration_ms"),
                truncated=bool(payload.get("truncated", False)),
            ),
        )
    if kind == HINT:
        return HintRevealed(
            at=at,
            index=_payload_int(payload, "index"),
            hint=Hint(_payload_text(payload, "text")),
        )
    if kind == SOLUTION:
        return SolutionSaved(at=at, source=_payload_text(payload, "source"))
    if kind == SUBMISSION:
        return SubmissionFailed(
            at=at, verdict=_verdict_from(_present(payload, "verdict"))
        )
    # Unreachable while the CHECK constraint holds, which is the point of having
    # it: a kind nothing handles can only arrive from a schema this file has not
    # been taught about, and guessing which event it meant would be worse.
    raise RowError(f"unknown attempt event kind: {kind!r}")


def _to_verdict(raw: object) -> Verdict:
    return _verdict_from(_decode(raw, "verdict"))


def _verdict_from(payload: object) -> Verdict:
    """A decoded verdict: the `verdict` column's, or a failed submission's."""
    if not isinstance(payload, list):
        raise RowError(f"verdict must be a JSON array, got {type(payload).__name__}")
    return Verdict(
        reports=tuple(
            _to_report(entry, position) for position, entry in enumerate(payload)
        )
    )


def _to_report(entry: object, position: int) -> CheckReport:
    if not isinstance(entry, dict):
        raise RowError(f"verdict[{position}] must be a JSON object")
    where = f"verdict[{position}]"
    return CheckReport(
        check_id=_payload_text(entry, "check_id", where=where),
        label=_payload_text(entry, "label", where=where),
        severity=Severity(_payload_text(entry, "severity", where=where)),
        passed=bool(_present(entry, "passed", where=where)),
        expected=_payload_optional_text(entry, "expected", where=where),
        actual=_payload_optional_text(entry, "actual", where=where),
        explanation=_payload_optional_text(entry, "explanation", where=where),
    )


def _to_claim(row: Mapping[str, object]) -> ComplexityClaim | None:
    """Both axes or neither, which the schema also refuses to store otherwise."""
    time = _required(row, "declared_time", optional=True)
    space = _required(row, "declared_space", optional=True)
    if time is None and space is None:
        return None
    if time is None or space is None:
        raise RowError(
            "a complexity claim needs both axes; the row has "
            f"declared_time={time!r} and declared_space={space!r}"
        )
    return ComplexityClaim(time=str(time), space=str(space))


# --- review cards -----------------------------------------------------------


def card_row(card: ReviewCard) -> dict[str, object]:
    """One row of `review_cards`, keyed by column name.

    `due_on` goes in as `YYYY-MM-DD` and `last_reviewed_at` as a full timestamp,
    which is the asymmetry the domain already has: a card comes due on a calendar
    day, and the moment it was reviewed is an instant. Storing the first as a
    timestamp would make `due_on <= :day` depend on a time of day nobody set.

    `stability` and `difficulty` go in as they are, `None` included. They are the
    one pair of columns here that is *expected* to be null for most of the table
    (0002): a card SM-2 wrote has no FSRS memory state and inventing one would be
    a fabricated history rather than a missing value.
    """
    return {
        "exercise_id": str(card.exercise_id),
        "state": card.state.value,
        "ease": card.ease,
        "interval_days": card.interval_days,
        "reps": card.reps,
        "lapses": card.lapses,
        "due_on": card.due_on.isoformat(),
        "last_reviewed_at": _isoformat(card.last_reviewed_at),
        "stability": card.stability,
        "difficulty": card.difficulty,
    }


def to_card(row: Mapping[str, object]) -> ReviewCard:
    """Rebuild one card. Every bound it carries is re-checked by the dataclass.

    Which is the point of the floor being in `ReviewCard` rather than only inside
    the scheduler: the scheduler is not the sole writer, a repository is, and an
    invariant that holds only while one function writes it is not an invariant.
    """
    return ReviewCard(
        exercise_id=ExerciseId(_text(row, "exercise_id")),
        state=CardState(_text(row, "state")),
        ease=_number(row, "ease"),
        interval_days=_integer(row, "interval_days"),
        reps=_integer(row, "reps"),
        lapses=_integer(row, "lapses"),
        due_on=_day(row, "due_on"),
        last_reviewed_at=_optional_timestamp(row, "last_reviewed_at"),
        stability=_optional_number(row, "stability"),
        difficulty=_optional_number(row, "difficulty"),
    )


# --- reading a row ----------------------------------------------------------
#
# Small and dull on purpose. Every one of these exists so that a column that is
# absent, null where it must not be, or of the wrong type names itself in the
# error instead of surfacing as a `TypeError` inside a value object's
# constructor.


def _required(
    row: Mapping[str, object], column: str, *, optional: bool = False
) -> object:
    try:
        value = row[column]
    except KeyError as exc:
        raise RowError(f"row has no {column!r} column") from exc
    if value is None and not optional:
        raise RowError(f"{column} is null")
    return value


def _text(row: Mapping[str, object], column: str) -> str:
    value = _required(row, column)
    if not isinstance(value, str):
        raise RowError(f"{column} must be text, got {type(value).__name__}")
    return value


def _integer(row: Mapping[str, object], column: str) -> int:
    value = _required(row, column)
    if not isinstance(value, int) or isinstance(value, bool):
        raise RowError(f"{column} must be an integer, got {type(value).__name__}")
    return value


def _number(row: Mapping[str, object], column: str) -> float:
    """A REAL column. An integer is accepted: SQLite stores 2.0 as 2 given the
    chance, and refusing it would make an ease of exactly 2 unreadable.
    """
    value = _required(row, column)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RowError(f"{column} must be a number, got {type(value).__name__}")
    return float(value)


def _optional_integer(row: Mapping[str, object], column: str) -> int | None:
    """A nullable INTEGER column. `None` is the value, not a missing one.

    `deadline_seconds` is NULL for every practice attempt, which is most of the
    table, so this is the common path rather than the degenerate one.
    `AttemptPolicy` is what holds NULL to meaning *untimed* — the mapper's job
    is to refuse a row that is the wrong type, not to decide what absence means.
    """
    value = _required(row, column, optional=True)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise RowError(f"{column} must be an integer, got {type(value).__name__}")
    return value


def _optional_number(row: Mapping[str, object], column: str) -> float | None:
    """A nullable REAL column, for the two 0002 added.

    Null is a value here rather than a fault, which is the whole difference from
    `_number`: a card SM-2 wrote has no stability, and `ReviewCard` is the thing
    that decides what that means.
    """
    if _required(row, column, optional=True) is None:
        return None
    return _number(row, column)


def _day(row: Mapping[str, object], column: str) -> date:
    """A calendar day, and only that.

    `date.fromisoformat` refuses a full timestamp, which is the behaviour wanted
    here: a timestamp in `due_on` means the writer and this file disagree about
    the column, and silently truncating it to a day would hide that.
    """
    text = _text(row, column)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise RowError(f"{column} is not an ISO 8601 date: {text!r}") from exc


def _timestamp(row: Mapping[str, object], column: str) -> datetime:
    """Parsed, not trusted: `Attempt` refuses a naive datetime, so a column
    written without an offset has to fail here rather than at the aggregate,
    where the message would not say which column it came from.
    """
    text = _text(row, column)
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise RowError(f"{column} is not an ISO 8601 timestamp: {text!r}") from exc


def _optional_timestamp(row: Mapping[str, object], column: str) -> datetime | None:
    return (
        None
        if _required(row, column, optional=True) is None
        else _timestamp(row, column)
    )


def _strings(row: Mapping[str, object], column: str) -> tuple[str, ...]:
    payload = _decode(_required(row, column), column)
    if not isinstance(payload, list) or any(
        not isinstance(item, str) for item in payload
    ):
        raise RowError(f"{column} must be a JSON array of strings")
    return tuple(str(item) for item in payload)


def _payload(row: Mapping[str, object]) -> Mapping[str, object]:
    payload = _decode(_required(row, "payload"), "payload")
    if not isinstance(payload, dict):
        raise RowError("payload must be a JSON object")
    return payload


def _decode(raw: object, where: str) -> object:
    if not isinstance(raw, str):
        raise RowError(f"{where} must be JSON text, got {type(raw).__name__}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RowError(f"{where} is not valid JSON: {exc}") from exc


def _present(
    payload: Mapping[str, object], field: str, *, where: str = "payload"
) -> object:
    try:
        return payload[field]
    except KeyError as exc:
        raise RowError(f"{where} has no {field!r} field") from exc


def _payload_text(
    payload: Mapping[str, object], field: str, *, where: str = "payload"
) -> str:
    value = _present(payload, field, where=where)
    if not isinstance(value, str):
        raise RowError(f"{where}.{field} must be a string, got {type(value).__name__}")
    return value


def _payload_optional_text(
    payload: Mapping[str, object], field: str, *, where: str = "payload"
) -> str | None:
    value = _present(payload, field, where=where)
    if value is None:
        return None
    if not isinstance(value, str):
        raise RowError(f"{where}.{field} must be a string or null")
    return value


def _payload_int(
    payload: Mapping[str, object], field: str, *, where: str = "payload"
) -> int:
    value = _present(payload, field, where=where)
    if not isinstance(value, int) or isinstance(value, bool):
        raise RowError(f"{where}.{field} must be an integer")
    return value


def _payload_strings(
    payload: Mapping[str, object], field: str, *, where: str = "payload"
) -> tuple[str, ...]:
    value = _present(payload, field, where=where)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise RowError(f"{where}.{field} must be an array of strings")
    return tuple(str(item) for item in value)


def _dump(payload: object) -> str:
    """Compact and key-sorted, so the same object always produces the same text.

    Which makes a row comparable in a test and a database diffable by eye — and
    costs nothing, because nothing ever queries inside these columns.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
