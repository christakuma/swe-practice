"""Domain <-> row, both directions, with no database in the room.

Unit tests, because the mappers are pure functions over `Mapping`s — which is the
reason they are pure functions over `Mapping`s. The translation is the part of
persistence that is easiest to get quietly wrong, and it would be a shame to only
ever exercise it through a SQLite connection that makes every case cost a file.

The first test is the one that matters: **the round trip, over an attempt that has
reached every state the aggregate can reach.** A mapper's failure mode is silence —
a field nobody reads back persists as `None` for a year — so the assertion is
object equality over the whole aggregate rather than a case per field, which would
pass for exactly the field nobody wrote a case for.

Everything after it is the other half: a row that is *wrong* has to say which
column, because the alternative is a `TypeError` from inside a value object's
constructor with no indication of where the value came from.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest

from practice.adapters.persistence.sqlite.mappers import (
    RowError,
    attempt_row,
    event_rows,
    to_attempt,
)
from practice.domain.attempt import (
    Attempt,
    AttemptPolicy,
    AttemptStatus,
    CommandResult,
    ComplexityClaim,
)
from practice.domain.errors import InvalidValueError
from practice.domain.exercise import Hint
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.verdict import CheckReport, Severity, Verdict

if TYPE_CHECKING:
    from collections.abc import Mapping

STARTED_AT = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)
ATTEMPT_ID = AttemptId(UUID("6f3a1c2e-0000-4000-8000-000000000001"))
EXERCISE_ID = ExerciseId("git/revert-a-pushed-commit")


def at(minutes: int) -> datetime:
    return STARTED_AT + timedelta(minutes=minutes)


def a_policy() -> AttemptPolicy:
    return AttemptPolicy(
        max_commands=25,
        hints=(Hint("Read build.sh first."), Hint("Your teammate has this commit.")),
        allowed_commands=frozenset({"git", "cat", "write"}),
    )


def a_verdict() -> Verdict:
    """One of each severity, and a failing report that carries its detail.

    The detail fields are the ones most likely to be dropped: they are optional,
    and a round trip over a passing check alone would never read them.
    """
    return Verdict(
        (
            CheckReport(
                check_id="content-restored",
                label="The committed tree matches",
                severity=Severity.REQUIRED,
                passed=True,
            ),
            CheckReport(
                check_id="history-preserved",
                label="The bad commit is still reachable",
                severity=Severity.ADVISORY,
                passed=False,
                expected="@c3 reachable from HEAD",
                actual="not reachable",
                explanation="Your teammate already has c3.",
            ),
        )
    )


def a_finished_attempt() -> Attempt:
    """Every field populated and all three kinds of event in the log."""
    attempt = Attempt(
        attempt_id=ATTEMPT_ID,
        exercise_id=EXERCISE_ID,
        policy=a_policy(),
        started_at=STARTED_AT,
    )
    attempt.reveal_next_hint(at=at(1))
    attempt.record_command(
        ["git", "revert", "--no-edit", "HEAD"],
        CommandResult(
            exit_code=1,
            stdout="[main dc52587] Revert",
            stderr="error: could not revert",
            duration_ms=42,
            truncated=True,
        ),
        at=at(2),
    )
    attempt.save_solution("def two_sum():\n    return ()\n", at=at(3))
    attempt.declare_complexity(ComplexityClaim(time="O(n)", space="O(n)"))
    attempt.complete(a_verdict(), at=at(4))
    return attempt


def roundtrip(attempt: Attempt) -> Attempt:
    return to_attempt(attempt_row(attempt), event_rows(attempt))


def equivalent(left: Attempt, right: Attempt) -> bool:
    """Field-by-field, because `Attempt` is the one mutable type in the domain and
    deliberately has no `__eq__` — two attempts with the same id are the same
    attempt, and defining equality by value would make that confusing.
    """
    return (
        left.id == right.id
        and left.exercise_id == right.exercise_id
        and left.policy == right.policy
        and left.started_at == right.started_at
        and left.finished_at == right.finished_at
        and left.status == right.status
        and left.events == right.events
        and left.verdict == right.verdict
        and left.declared_complexity == right.declared_complexity
    )


# --- the round trip ---------------------------------------------------------


def test_a_finished_attempt_survives_the_round_trip_intact() -> None:
    original = a_finished_attempt()

    assert equivalent(roundtrip(original), original)


def test_an_untouched_active_attempt_survives_too() -> None:
    """The other end of the range: no events, no verdict, no claim. Every
    nullable column is null, which is where an over-eager mapper trips.
    """
    original = Attempt(
        attempt_id=ATTEMPT_ID,
        exercise_id=EXERCISE_ID,
        policy=a_policy(),
        started_at=STARTED_AT,
    )

    restored = roundtrip(original)

    assert equivalent(restored, original)
    assert restored.status is AttemptStatus.ACTIVE
    assert restored.events == ()


def test_an_abandoned_attempt_keeps_its_log_and_has_no_verdict() -> None:
    original = Attempt(
        attempt_id=ATTEMPT_ID,
        exercise_id=EXERCISE_ID,
        policy=a_policy(),
        started_at=STARTED_AT,
    )
    original.record_command(["git", "status"], CommandResult(exit_code=0), at=at(1))
    original.abandon(at=at(2))

    restored = roundtrip(original)

    assert restored.status is AttemptStatus.ABANDONED
    assert restored.verdict is None
    assert restored.command_count == 1


def test_command_output_and_its_flags_survive() -> None:
    """Named separately from the round trip because these five fields are what a
    replay *shows*, and a transcript that lost its stderr would still round-trip
    as an attempt with the right number of commands.
    """
    original = a_finished_attempt()

    (command,) = roundtrip(original).commands

    assert command.argv == ("git", "revert", "--no-edit", "HEAD")
    assert command.result.exit_code == 1
    assert command.result.stdout == "[main dc52587] Revert"
    assert command.result.stderr == "error: could not revert"
    assert command.result.duration_ms == 42
    assert command.result.truncated is True


def test_a_revealed_hint_keeps_the_text_it_was_shown_as() -> None:
    """The text as well as the index, so the log records *which* hint was shown
    even if the exercise is later edited (PLAN.md §4.3).
    """
    original = a_finished_attempt()

    revealed = roundtrip(original).events[0]

    assert getattr(revealed, "index", None) == 0
    assert getattr(revealed, "hint", None) == Hint("Read build.sh first.")


def test_the_verdict_keeps_its_order_and_its_optional_detail() -> None:
    restored = roundtrip(a_finished_attempt())
    assert restored.verdict is not None

    first, second = restored.verdict.reports

    assert [report.check_id for report in restored.verdict.reports] == [
        "content-restored",
        "history-preserved",
    ]
    assert first.severity is Severity.REQUIRED
    assert second.severity is Severity.ADVISORY
    assert second.expected == "@c3 reachable from HEAD"
    assert second.explanation == "Your teammate already has c3."
    assert restored.verdict.outcome == a_verdict().outcome


# --- what a row looks like --------------------------------------------------


def test_the_row_is_keyed_by_column_name() -> None:
    row = attempt_row(a_finished_attempt())

    assert row["id"] == str(ATTEMPT_ID)
    assert row["exercise_id"] == "git/revert-a-pushed-commit"
    assert row["status"] == "completed"
    assert row["started_at"] == STARTED_AT.isoformat()
    assert row["declared_time"] == "O(n)"
    assert row["max_commands"] == 25


def test_the_allowlist_is_stored_in_a_stable_order() -> None:
    """A `frozenset`'s iteration order is stable within a process and not across
    them, so without sorting, a stored row would depend on which process wrote it
    — and two saves of the same attempt would produce different bytes.
    """
    row = attempt_row(a_finished_attempt())

    assert json.loads(str(row["allowed_commands"])) == ["cat", "git", "write"]


def test_every_event_is_positioned_in_log_order() -> None:
    """`position`, not the timestamp: `Attempt` allows two events to share one, so
    the order the log was appended in is the only thing replay can rely on.
    """
    rows = event_rows(a_finished_attempt())

    assert [row["position"] for row in rows] == [0, 1, 2]
    assert [row["kind"] for row in rows] == ["hint", "command", "solution"]
    assert {row["attempt_id"] for row in rows} == {str(ATTEMPT_ID)}


def test_the_same_attempt_always_produces_the_same_bytes() -> None:
    """Which is what makes a row comparable in a test and a database diffable by
    eye. It costs nothing, because nothing ever queries inside a JSON column.
    """
    first, second = a_finished_attempt(), a_finished_attempt()

    assert attempt_row(first) == attempt_row(second)
    assert event_rows(first) == event_rows(second)


# --- rows that are wrong ---------------------------------------------------


def a_row(**overrides: Any) -> dict[str, object]:
    row = attempt_row(a_finished_attempt())
    row.update(overrides)
    return row


def an_event(**overrides: Any) -> dict[str, object]:
    row = dict(event_rows(a_finished_attempt())[1])
    row.update(overrides)
    return row


def test_a_missing_column_names_itself() -> None:
    row = a_row()
    del row["status"]

    with pytest.raises(RowError, match="no 'status' column"):
        to_attempt(row, [])


def test_a_null_where_null_is_impossible_names_itself() -> None:
    with pytest.raises(RowError, match="started_at is null"):
        to_attempt(a_row(started_at=None), [])


@pytest.mark.parametrize(
    ("column", "value", "expected"),
    [
        ("status", 3, "must be text"),
        ("max_commands", "twenty-five", "must be an integer"),
        ("max_commands", True, "must be an integer"),
        ("started_at", "not-a-date", "not an ISO 8601 timestamp"),
        ("hints", "[1, 2]", "array of strings"),
        ("hints", "{}", "array of strings"),
        ("allowed_commands", "not json", "not valid JSON"),
        ("verdict", '{"nope": 1}', "must be a JSON array"),
        ("verdict", "[3]", r"verdict\[0\] must be a JSON object"),
    ],
)
def test_a_column_of_the_wrong_shape_says_which_and_why(
    column: str, value: object, expected: str
) -> None:
    """Each of these is a schema the mapper has not been taught about, and each
    one is a message naming the column rather than a traceback from inside a
    value object three frames down.
    """
    with pytest.raises(RowError, match=expected):
        to_attempt(a_row(**{column: value}), [])


def test_an_unparseable_value_still_reaches_the_domain_for_validation() -> None:
    """A row that is *shaped* correctly and holds something impossible is the
    domain's refusal, not the mapper's — `InvalidValueError`, from the value
    object that knows what a valid one looks like.
    """
    with pytest.raises(InvalidValueError, match="exercise id"):
        to_attempt(a_row(exercise_id="not/a/valid/id"), [])


def test_half_a_complexity_claim_is_refused() -> None:
    """Both axes or neither: a claim about one cannot disagree with an expectation
    about two, which the CHECK constraint also refuses to store.
    """
    with pytest.raises(RowError, match="both axes"):
        to_attempt(a_row(declared_space=None), [])


def test_an_unknown_event_kind_is_refused_rather_than_guessed_at() -> None:
    """Unreachable while the CHECK constraint holds, which is the point of having
    both: an event kind nothing handles can only come from a schema this mapper
    has not been taught about, and picking an event type for it would be worse.
    """
    with pytest.raises(RowError, match="unknown attempt event kind"):
        to_attempt(a_row(), [an_event(kind="telepathy")])


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ('{"argv": "git log"}', "argv must be an array"),
        ('{"argv": [1]}', "argv must be an array"),
        ('{"argv": ["git"]}', "no 'exit_code' field"),
        ('{"argv": ["git"], "exit_code": "0"}', "exit_code must be an integer"),
        ("[]", "payload must be a JSON object"),
        ("not json", "payload is not valid JSON"),
    ],
)
def test_a_malformed_event_payload_says_which_field(
    payload: str, expected: str
) -> None:
    with pytest.raises(RowError, match=expected):
        to_attempt(a_row(), [an_event(payload=payload)])


def test_events_are_taken_in_the_order_given_not_re_sorted() -> None:
    """Ordering is the query's job. Re-sorting by `position` here would hide a
    missing `ORDER BY` that another caller would then hit, so a log handed over
    out of order is a refusal — from the aggregate, which is where the rule is.
    """
    first, second = event_rows(a_finished_attempt())[:2]

    with pytest.raises(InvalidValueError, match="out of order"):
        to_attempt(a_row(), [second, first])


def test_a_verdict_report_missing_a_field_names_the_report() -> None:
    broken = json.dumps([{"check_id": "x", "label": "y", "severity": "required"}])

    with pytest.raises(RowError, match=r"verdict\[0\] has no 'passed' field"):
        to_attempt(a_row(verdict=broken), [])


def test_a_mapping_is_all_a_mapper_needs() -> None:
    """The property the whole file rests on: no connection, no `sqlite3.Row`, no
    database. A plain dict is a valid row, which is why these tests are units.
    """
    row: Mapping[str, object] = dict(attempt_row(a_finished_attempt()))

    assert to_attempt(row, []).id == ATTEMPT_ID
