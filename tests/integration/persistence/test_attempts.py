"""`SqliteAttemptRepository` against real SQLite.

Integration, because what is left in the repository once the mappers are pure is
SQL, and SQL is only confirmed by a database. Every test here is about something a
dict cannot have an opinion on: that a second save replaces rather than duplicates,
that a shortened event log does not leave orphan rows behind, that ordering is
explicit, and that an attempt survives a process which no longer exists.

**The pair of tests at the end is the phase's exit criterion.** A repository built
over one file, written to, dropped, and rebuilt — which is what two `practice`
invocations are — hands back the same attempt. That is the whole of "attempts
survive a restart", at the lowest layer that can state it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest

from practice.adapters.persistence.sqlite import Database, SqliteAttemptRepository
from practice.domain.attempt import (
    Attempt,
    AttemptPolicy,
    AttemptStatus,
    CommandResult,
    ComplexityClaim,
)
from practice.domain.exercise import Hint
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.verdict import CheckReport, Severity, Verdict

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.ports import AttemptRepository

STARTED_AT = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)
REVERT = ExerciseId("git/revert-a-pushed-commit")
TWO_SUM = ExerciseId("katas/two-sum")

OK = CommandResult(exit_code=0, stdout="ok")


def an_id(n: int) -> AttemptId:
    return AttemptId(UUID(f"6f3a1c2e-0000-4000-8000-{n:012d}"))


def at(minutes: int) -> datetime:
    return STARTED_AT + timedelta(minutes=minutes)


def a_policy() -> AttemptPolicy:
    return AttemptPolicy(
        max_commands=25,
        hints=(Hint("Read build.sh first."),),
        allowed_commands=frozenset({"git", "cat"}),
    )


def a_verdict() -> Verdict:
    return Verdict(
        (
            CheckReport(
                check_id="content-restored",
                label="The committed tree matches",
                severity=Severity.REQUIRED,
                passed=True,
            ),
        )
    )


def an_attempt(
    n: int = 1, *, exercise_id: ExerciseId = REVERT, minutes: int = 0
) -> Attempt:
    return Attempt(
        attempt_id=an_id(n),
        exercise_id=exercise_id,
        policy=a_policy(),
        started_at=at(minutes),
    )


@pytest.fixture
def database(tmp_path: Path) -> Database:
    return Database(tmp_path / "practice.db")


@pytest.fixture
def attempts(database: Database) -> SqliteAttemptRepository:
    return SqliteAttemptRepository(database)


def events_in(database: Database) -> int:
    with database.connect() as connection:
        return int(
            connection.execute("SELECT count(*) AS n FROM attempt_events").fetchone()[
                "n"
            ]
        )


# --- the port ---------------------------------------------------------------


def test_it_satisfies_the_attempt_repository_port(database: Database) -> None:
    """The annotation is the assertion, as everywhere else: an adapter never
    subclasses its port, so mypy under `--strict` is the only thing that notices a
    drift. Asserted here rather than in `tests/unit/test_ports.py` because this one
    needs a file on disk, and a unit test that opened a database would not be one.
    """
    repository: AttemptRepository = SqliteAttemptRepository(database)
    attempt = an_attempt()

    repository.save(attempt)

    assert repository.get(attempt.id) is not None
    assert len(repository.history_for(REVERT)) == 1
    assert len(repository.active()) == 1


# --- saving ----------------------------------------------------------------


def test_an_attempt_comes_back_as_it_went_in(
    attempts: SqliteAttemptRepository,
) -> None:
    attempt = an_attempt()
    attempt.reveal_next_hint(at=at(1))
    attempt.record_command(["git", "log"], OK, at=at(2))
    attempt.declare_complexity(ComplexityClaim(time="O(n)", space="O(1)"))
    attempt.complete(a_verdict(), at=at(3))

    attempts.save(attempt)
    restored = attempts.get(attempt.id)

    assert restored is not None
    assert restored.status is AttemptStatus.COMPLETED
    assert restored.events == attempt.events
    assert restored.verdict == attempt.verdict
    assert restored.declared_complexity == attempt.declared_complexity
    assert restored.policy == attempt.policy


def test_saving_twice_replaces_the_row_rather_than_duplicating_it(
    attempts: SqliteAttemptRepository,
) -> None:
    """The normal case, not an edge: an attempt is saved when it starts, after every
    command, and again when it is graded.
    """
    attempt = an_attempt()
    attempts.save(attempt)

    attempt.record_command(["git", "log"], OK, at=at(1))
    attempt.complete(a_verdict(), at=at(2))
    attempts.save(attempt)

    assert len(attempts) == 1
    restored = attempts.get(attempt.id)
    assert restored is not None
    assert restored.status is AttemptStatus.COMPLETED


def test_the_event_log_is_rewritten_not_appended_to(
    attempts: SqliteAttemptRepository, database: Database
) -> None:
    """Three saves of a growing log must leave three events, not six.

    The thing this rules out is an `INSERT` with no `DELETE` in front of it, which
    passes `get` — the mapper would just see the first three rows in position order
    — and shows up as a duplicate only once the log is long enough to notice.
    """
    attempt = an_attempt()
    for index in range(3):
        attempt.record_command(["git", "log"], OK, at=at(index + 1))
        attempts.save(attempt)

    assert events_in(database) == 3
    restored = attempts.get(attempt.id)
    assert restored is not None
    assert restored.command_count == 3


def test_an_attempt_that_was_never_saved_is_none(
    attempts: SqliteAttemptRepository,
) -> None:
    """The common case now rather than the exceptional one: every id from a
    database that has since been deleted lands here, as does a stale URL.
    """
    assert attempts.get(an_id(99)) is None


def test_events_are_deleted_with_their_attempt(
    attempts: SqliteAttemptRepository, database: Database
) -> None:
    """`ON DELETE CASCADE`, which only fires because `foreign_keys` is set on every
    connection — it is per-connection and off by default. Nothing deletes an
    attempt yet; this is the constraint that stops an event log outliving the
    attempt it describes when something does.
    """
    attempt = an_attempt()
    attempt.record_command(["git", "log"], OK, at=at(1))
    attempts.save(attempt)

    with database.connect() as connection:
        connection.execute("DELETE FROM attempts WHERE id = ?", (str(attempt.id),))

    assert events_in(database) == 0


# --- reading ---------------------------------------------------------------


def test_history_is_oldest_first_and_only_for_that_exercise(
    attempts: SqliteAttemptRepository,
) -> None:
    """Explicitly ordered, where the in-memory store gets it from an
    insertion-ordered dict. Saved newest-first on purpose, so a missing `ORDER BY`
    fails rather than passing by accident of insertion order.
    """
    attempts.save(an_attempt(2, minutes=20))
    attempts.save(an_attempt(1, minutes=10))
    attempts.save(an_attempt(3, exercise_id=TWO_SUM, minutes=30))

    history = attempts.history_for(REVERT)

    assert [attempt.id for attempt in history] == [an_id(1), an_id(2)]
    assert [attempt.id for attempt in attempts.history_for(TWO_SUM)] == [an_id(3)]


def test_history_for_an_exercise_nobody_has_attempted_is_empty(
    attempts: SqliteAttemptRepository,
) -> None:
    assert attempts.history_for(TWO_SUM) == ()


def test_history_carries_each_attempts_own_events(
    attempts: SqliteAttemptRepository,
) -> None:
    """Loaded in two queries rather than one per attempt, which is only correct if
    the events end up attached to the right attempt — the thing a grouped query
    can get wrong and a per-attempt loop cannot.
    """
    first, second = an_attempt(1, minutes=10), an_attempt(2, minutes=20)
    first.record_command(["git", "log"], OK, at=at(11))
    second.record_command(["git", "status"], OK, at=at(21))
    second.record_command(["git", "diff"], OK, at=at(22))
    attempts.save(second)
    attempts.save(first)

    history = attempts.history_for(REVERT)

    assert [attempt.command_count for attempt in history] == [1, 2]
    assert [command.argv for command in history[0].commands] == [("git", "log")]
    assert [command.argv for command in history[1].commands] == [
        ("git", "status"),
        ("git", "diff"),
    ]


def test_active_holds_what_has_neither_been_submitted_nor_abandoned(
    attempts: SqliteAttemptRepository,
) -> None:
    """The query the whole attempt table exists for (PLAN.md §8.1): the resume
    prompt offers these, and `gc` calls a workspace without one an orphan.
    """
    still_going = an_attempt(1, minutes=10)
    graded = an_attempt(2, minutes=20)
    graded.complete(a_verdict(), at=at(25))
    given_up = an_attempt(3, minutes=30)
    given_up.abandon(at=at(35))
    for attempt in (still_going, graded, given_up):
        attempts.save(attempt)

    assert [attempt.id for attempt in attempts.active()] == [an_id(1)]


def test_an_attempt_leaves_active_when_it_is_completed(
    attempts: SqliteAttemptRepository,
) -> None:
    """The transition, not just the two states: an attempt saved active and then
    saved again completed must not stay in the active set — which is what an
    `INSERT OR IGNORE` would have produced.
    """
    attempt = an_attempt()
    attempts.save(attempt)
    assert len(attempts.active()) == 1

    attempt.complete(a_verdict(), at=at(1))
    attempts.save(attempt)

    assert attempts.active() == ()


def test_active_is_empty_on_a_fresh_database(
    attempts: SqliteAttemptRepository,
) -> None:
    assert attempts.active() == ()


def test_completed_holds_only_graded_attempts_oldest_finish_first(
    attempts: SqliteAttemptRepository,
) -> None:
    """`active`'s counterpart and the progress page's only query.

    Ordered by *finish* and not by start, which is the order a history reads in
    and the order a streak is counted from -- and which differs from the start
    order whenever one attempt is left open across another.
    """
    still_going = an_attempt(1, minutes=10)
    slow = an_attempt(2, minutes=20)
    slow.complete(a_verdict(), at=at(90))
    quick = an_attempt(3, minutes=30)
    quick.complete(a_verdict(), at=at(35))
    given_up = an_attempt(4, minutes=40)
    given_up.abandon(at=at(45))
    for attempt in (still_going, slow, quick, given_up):
        attempts.save(attempt)

    assert [attempt.id for attempt in attempts.completed()] == [an_id(3), an_id(2)]


def test_completed_carries_the_event_log_like_every_other_listing(
    attempts: SqliteAttemptRepository,
) -> None:
    """Two queries and not one per attempt, which is the shape that matters here
    more than anywhere: this is the listing with no upper bound on its size.
    """
    attempt = an_attempt(1)
    attempt.record_command(["git", "log"], CommandResult(exit_code=0), at=at(1))
    attempt.complete(a_verdict(), at=at(2))
    attempts.save(attempt)

    (loaded,) = attempts.completed()

    assert [command.argv for command in loaded.commands] == [("git", "log")]


def test_completed_is_empty_on_a_fresh_database(
    attempts: SqliteAttemptRepository,
) -> None:
    assert attempts.completed() == ()


# --- surviving a restart ---------------------------------------------------


def test_an_attempt_outlives_the_repository_that_saved_it(tmp_path: Path) -> None:
    """Two repositories over one file, which is what two `practice` invocations
    are. Until this phase an attempt could not outlive the process that started it,
    and the CLI said so in its own docstring.
    """
    path = tmp_path / "practice.db"
    attempt = an_attempt()
    attempt.record_command(["git", "log"], OK, at=at(1))
    SqliteAttemptRepository(Database(path)).save(attempt)

    restored = SqliteAttemptRepository(Database(path)).get(attempt.id)

    assert restored is not None
    assert restored.is_active
    assert [command.argv for command in restored.commands] == [("git", "log")]


def test_a_restored_attempt_can_be_carried_on_and_saved_again(
    tmp_path: Path,
) -> None:
    """Resume, at the storage layer: load, do one more thing, store it, and have a
    third reader see both. The aggregate's forward-only timestamp guard is rebuilt
    with the log, so the continuation has to come *after* what was stored.
    """
    path = tmp_path / "practice.db"
    attempt = an_attempt()
    attempt.record_command(["git", "log"], OK, at=at(1))
    SqliteAttemptRepository(Database(path)).save(attempt)

    resumed = SqliteAttemptRepository(Database(path)).get(attempt.id)
    assert resumed is not None
    resumed.record_command(["git", "status"], OK, at=at(2))
    resumed.complete(a_verdict(), at=at(3))
    SqliteAttemptRepository(Database(path)).save(resumed)

    final = SqliteAttemptRepository(Database(path)).get(attempt.id)
    assert final is not None
    assert final.status is AttemptStatus.COMPLETED
    assert [command.argv for command in final.commands] == [
        ("git", "log"),
        ("git", "status"),
    ]


def test_the_repository_describes_which_database_it_is_over(
    database: Database,
) -> None:
    """A `repr` that names the file, because the first question about a repository
    that cannot find an attempt is which database it was looking in.
    """
    assert str(database.path) in repr(SqliteAttemptRepository(database))
