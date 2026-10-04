"""The Attempt aggregate: one test per invariant it claims to enforce.

These are the tests that justify the AttemptPolicy existing at all. If the limits
were not copied onto the aggregate, every assertion below would have to be made
about a use case instead — and would then only hold for the code paths someone
remembered to write it for.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest

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
)
from practice.domain.errors import (
    AttemptStateError,
    InvalidValueError,
    PolicyViolationError,
)
from practice.domain.exercise import (
    CheckSpec,
    ComplexityExpectation,
    Difficulty,
    Exercise,
    ExerciseKind,
    GitScenarioSpec,
    Hint,
    KataSpec,
)
from practice.domain.ids import AttemptId, ExerciseId, tag
from practice.domain.verdict import CheckReport, Severity, Verdict

STARTED_AT = datetime(2026, 9, 30, 9, 0, tzinfo=UTC)
ATTEMPT_ID = AttemptId(UUID("6f3a1c2e-0000-4000-8000-000000000001"))
EXERCISE_ID = ExerciseId("git/revert-a-pushed-commit")

HINTS = (
    Hint("Read build.sh, then parser.py."),
    Hint("Your teammate already has this commit."),
)
OK = CommandResult(exit_code=0, stdout="ok")


def at(minutes: int) -> datetime:
    return STARTED_AT + timedelta(minutes=minutes)


def a_policy(**overrides: Any) -> AttemptPolicy:
    base = AttemptPolicy(
        max_commands=3,
        hints=HINTS,
        allowed_commands=frozenset({"git", "cat"}),
    )
    return replace(base, **overrides)


def an_attempt(policy: AttemptPolicy | None = None) -> Attempt:
    return Attempt(
        attempt_id=ATTEMPT_ID,
        exercise_id=EXERCISE_ID,
        policy=policy if policy is not None else a_policy(),
        started_at=STARTED_AT,
    )


def a_verdict(*, passed: bool = True) -> Verdict:
    return Verdict(
        (
            CheckReport(
                check_id="content-restored",
                label="tree matches",
                severity=Severity.REQUIRED,
                passed=passed,
            ),
        )
    )


class TestConstruction:
    def test_starts_active_and_empty(self) -> None:
        attempt = an_attempt()

        assert attempt.id == ATTEMPT_ID
        assert attempt.exercise_id == EXERCISE_ID
        assert attempt.status is AttemptStatus.ACTIVE
        assert attempt.is_active is True
        assert attempt.events == ()
        assert attempt.command_count == 0
        assert attempt.hints_revealed == 0
        assert attempt.finished_at is None
        assert attempt.verdict is None
        assert attempt.declared_complexity is None
        assert attempt.started_at == STARTED_AT
        assert attempt.policy.max_commands == 3

    def test_refuses_a_naive_start_time(self) -> None:
        with pytest.raises(InvalidValueError, match="timezone-aware"):
            Attempt(
                attempt_id=ATTEMPT_ID,
                exercise_id=EXERCISE_ID,
                policy=a_policy(),
                started_at=datetime(2026, 9, 30, 9, 0),  # noqa: DTZ001
            )

    def test_repr_names_the_exercise_and_the_state(self) -> None:
        assert "revert-a-pushed-commit" in repr(an_attempt())
        assert "active" in repr(an_attempt())


class TestAttemptPolicy:
    def test_a_scenario_policy_copies_the_budget_and_the_allowlist(self) -> None:
        exercise = a_scenario_exercise()

        policy = AttemptPolicy.for_exercise(exercise)

        assert policy.max_commands == 25
        assert policy.allowed_commands == frozenset({"git", "cat"})
        assert policy.hints == exercise.hints
        assert policy.hint_count == 2

    def test_a_kata_policy_has_no_command_budget_at_all(self) -> None:
        """A kata has no command console, so every command against one is out of
        policy — which is the honest encoding rather than a special case.
        """
        policy = AttemptPolicy.for_exercise(a_kata_exercise())

        assert policy.max_commands == 0
        assert policy.allowed_commands == frozenset()

    def test_rejects_a_negative_budget(self) -> None:
        with pytest.raises(InvalidValueError):
            a_policy(max_commands=-1)

    def test_a_practice_policy_is_the_default_and_is_untimed(self) -> None:
        """The regression that matters most in Phase 15: every attempt that
        existed before interview mode has to keep behaving identically, and the
        way that is guaranteed is that `mode` defaults and the deadline is
        `None`.
        """
        policy = AttemptPolicy.for_exercise(a_scenario_exercise())

        assert policy.mode is AttemptMode.PRACTICE
        assert policy.is_interview is False
        assert policy.deadline_seconds is None
        assert policy.reveals_workspace is True
        assert policy.hint_count == 2


class TestInterviewPolicy:
    def test_withholds_the_hints_and_sets_a_deadline(self) -> None:
        exercise = a_scenario_exercise()

        policy = AttemptPolicy.for_exercise(exercise, mode=AttemptMode.INTERVIEW)

        assert policy.is_interview is True
        assert policy.hints == ()
        assert policy.hint_count == 0
        assert policy.deadline_seconds == 10 * 60

    def test_the_deadline_is_the_authors_own_estimate_and_nothing_else(self) -> None:
        """Not a multiple of it. An interview is the estimate, and a tool that
        granted half as long again would be grading against a number no
        exercise states.
        """
        exercise = a_kata_exercise()
        assert exercise.estimated_minutes == 15

        policy = AttemptPolicy.for_exercise(exercise, mode=AttemptMode.INTERVIEW)

        assert policy.deadline_seconds == 15 * 60

    def test_withdraws_the_workspace_path(self) -> None:
        policy = AttemptPolicy.for_exercise(
            a_kata_exercise(), mode=AttemptMode.INTERVIEW
        )

        assert policy.reveals_workspace is False

    def test_keeps_the_command_budget_and_the_allowlist_untouched(self) -> None:
        """An interview that took the console away would not be a harder
        exercise, it would be an unsolvable one.
        """
        policy = AttemptPolicy.for_exercise(
            a_scenario_exercise(), mode=AttemptMode.INTERVIEW
        )

        assert policy.max_commands == 25
        assert policy.allowed_commands == frozenset({"git", "cat"})

    @pytest.mark.parametrize(
        ("kind", "minutes"),
        [(ExerciseKind.GIT_SCENARIO, 10), (ExerciseKind.KATA, 15)],
    )
    def test_nothing_about_the_mode_is_kind_specific(
        self, kind: ExerciseKind, minutes: int
    ) -> None:
        """The claim `for_exercise`'s docstring makes: the mode is applied before
        the kind is looked at, so every kind withholds and times identically.
        """
        exercise = (
            a_scenario_exercise()
            if kind is ExerciseKind.GIT_SCENARIO
            else a_kata_exercise()
        )

        policy = AttemptPolicy.for_exercise(exercise, mode=AttemptMode.INTERVIEW)

        assert policy.hints == ()
        assert policy.deadline_seconds == minutes * 60

    def test_a_mode_and_a_deadline_that_disagree_are_refused(self) -> None:
        with pytest.raises(InvalidValueError, match="disagree"):
            a_policy(mode=AttemptMode.INTERVIEW, deadline_seconds=None, hints=())

    def test_a_practice_run_cannot_be_timed(self) -> None:
        """The other direction of the same guard. A deadline nothing shows and
        nothing grades is a state that would have to be handled somewhere.
        """
        with pytest.raises(InvalidValueError, match="disagree"):
            a_policy(mode=AttemptMode.PRACTICE, deadline_seconds=600)

    def test_an_interview_policy_cannot_carry_hints(self) -> None:
        with pytest.raises(InvalidValueError, match="withholds hints"):
            a_policy(mode=AttemptMode.INTERVIEW, deadline_seconds=600, hints=HINTS)

    def test_rejects_a_deadline_of_no_time_at_all(self) -> None:
        with pytest.raises(InvalidValueError, match="at least 1"):
            a_policy(mode=AttemptMode.INTERVIEW, deadline_seconds=0, hints=())


class TestRecordCommand:
    def test_records_a_command_and_counts_it(self) -> None:
        attempt = an_attempt()

        event = attempt.record_command(["git", "status"], OK, at=at(1))

        assert attempt.command_count == 1
        assert attempt.remaining_commands == 2
        assert attempt.commands == (event,)
        assert isinstance(attempt.events[0], CommandRun)
        assert event.program == "git"
        assert event.command_line == "git status"

    def test_the_command_line_is_normalised_for_the_process_assertions(self) -> None:
        """`command_used` matches a pattern against this string, so it must not
        depend on how the solver spaced their arguments.
        """
        attempt = an_attempt()

        event = attempt.record_command(
            ["git", "push", "--force", "origin", "main"], OK, at=at(1)
        )

        assert event.command_line == "git push --force origin main"

    def test_refuses_a_command_the_exercise_does_not_allow(self) -> None:
        attempt = an_attempt()

        with pytest.raises(PolicyViolationError, match="not allowed"):
            attempt.record_command(["curl", "example.com"], OK, at=at(1))

        assert attempt.command_count == 0

    def test_the_message_lists_what_is_allowed(self) -> None:
        attempt = an_attempt()

        with pytest.raises(PolicyViolationError, match="cat, git"):
            attempt.record_command(["rm", "-rf", "."], OK, at=at(1))

    def test_refuses_an_empty_command(self) -> None:
        with pytest.raises(InvalidValueError, match="empty command"):
            an_attempt().record_command([], OK, at=at(1))

    def test_enforces_the_command_budget(self) -> None:
        attempt = an_attempt(a_policy(max_commands=2))

        attempt.record_command(["git", "log"], OK, at=at(1))
        attempt.record_command(["git", "status"], OK, at=at(2))

        assert attempt.remaining_commands == 0
        with pytest.raises(PolicyViolationError, match="budget exhausted"):
            attempt.record_command(["git", "diff"], OK, at=at(3))

    def test_a_kata_attempt_can_run_no_commands_at_all(self) -> None:
        attempt = an_attempt(AttemptPolicy.for_exercise(a_kata_exercise()))

        with pytest.raises(PolicyViolationError):
            attempt.record_command(["git", "log"], OK, at=at(1))

    def test_records_a_failing_command_just_the_same(self) -> None:
        """The log is a record of what happened, not of what worked."""
        attempt = an_attempt()
        failed = CommandResult(exit_code=128, stderr="fatal: bad revision")

        event = attempt.record_command(["git", "show", "nope"], failed, at=at(1))

        assert event.result.succeeded is False
        assert attempt.command_count == 1


class TestHints:
    def test_reveals_hints_in_order(self) -> None:
        attempt = an_attempt()

        first = attempt.reveal_next_hint(at=at(1))
        second = attempt.reveal_next_hint(at=at(2))

        assert first == HINTS[0]
        assert second == HINTS[1]
        assert attempt.hints_revealed == 2
        assert attempt.remaining_hints == 0

    def test_the_log_records_which_hint_was_shown(self) -> None:
        attempt = an_attempt()

        attempt.reveal_next_hint(at=at(1))

        event = attempt.events[0]
        assert isinstance(event, HintRevealed)
        assert event.index == 0
        assert event.hint == HINTS[0]

    def test_cannot_reveal_more_hints_than_the_policy_holds(self) -> None:
        attempt = an_attempt()
        attempt.reveal_next_hint(at=at(1))
        attempt.reveal_next_hint(at=at(2))

        with pytest.raises(PolicyViolationError, match="no hints left"):
            attempt.reveal_next_hint(at=at(3))

    def test_an_exercise_with_no_hints_has_none_to_give(self) -> None:
        attempt = an_attempt(a_policy(hints=()))

        with pytest.raises(PolicyViolationError):
            attempt.reveal_next_hint(at=at(1))


class TestSolutionsAndComplexity:
    def test_saves_a_solution_snapshot(self) -> None:
        attempt = an_attempt()

        attempt.save_solution("def two_sum(): ...", at=at(1))

        event = attempt.events[0]
        assert isinstance(event, SolutionSaved)
        assert event.source == "def two_sum(): ..."

    def test_complexity_can_be_declared_and_replaced_before_submission(self) -> None:
        attempt = an_attempt()

        attempt.declare_complexity(ComplexityClaim(time="O(n^2)", space="O(1)"))
        attempt.declare_complexity(ComplexityClaim(time="O(n)", space="O(n)"))

        assert attempt.declared_complexity == ComplexityClaim(time="O(n)", space="O(n)")

    def test_a_claim_needs_both_axes(self) -> None:
        with pytest.raises(InvalidValueError, match="both time and space"):
            ComplexityClaim(time="O(n)", space=" ")

    def test_a_claim_agrees_across_spacing_and_case(self) -> None:
        claim = ComplexityClaim(time=" o(N log n) ", space="O(1)")
        expectation = ComplexityExpectation(
            expected_time="O(n log N)", expected_space="o( 1 )"
        )

        assert claim.agrees_with(expectation) is True

    def test_a_claim_that_differs_on_either_axis_disagrees(self) -> None:
        expectation = ComplexityExpectation(expected_time="O(n)", expected_space="O(n)")

        assert (
            ComplexityClaim(time="O(n)", space="O(1)").agrees_with(expectation) is False
        )
        assert (
            ComplexityClaim(time="O(n^2)", space="O(n)").agrees_with(expectation)
            is False
        )


class TestCompletion:
    def test_completing_attaches_the_verdict_and_closes_the_attempt(self) -> None:
        attempt = an_attempt()
        verdict = a_verdict()

        attempt.complete(verdict, at=at(10))

        assert attempt.verdict is verdict
        assert attempt.finished_at == at(10)
        assert attempt.status is AttemptStatus.COMPLETED
        assert attempt.is_active is False

    def test_cannot_complete_twice(self) -> None:
        attempt = an_attempt()
        attempt.complete(a_verdict(), at=at(10))

        with pytest.raises(AttemptStateError, match="completed"):
            attempt.complete(a_verdict(), at=at(11))

    def test_a_failing_verdict_still_completes_the_attempt(self) -> None:
        attempt = an_attempt()

        attempt.complete(a_verdict(passed=False), at=at(10))

        assert attempt.status is AttemptStatus.COMPLETED

    @pytest.mark.parametrize(
        ("action", "args"),
        [
            ("record_command", (["git", "log"], OK)),
            ("reveal_next_hint", ()),
            ("save_solution", ("source",)),
        ],
    )
    def test_no_events_may_be_recorded_after_completion(
        self, action: str, args: tuple[object, ...]
    ) -> None:
        attempt = an_attempt()
        attempt.complete(a_verdict(), at=at(10))

        with pytest.raises(AttemptStateError):
            getattr(attempt, action)(*args, at=at(11))

    def test_complexity_cannot_be_declared_after_completion(self) -> None:
        attempt = an_attempt()
        attempt.complete(a_verdict(), at=at(10))

        with pytest.raises(AttemptStateError, match="declare complexity"):
            attempt.declare_complexity(ComplexityClaim(time="O(n)", space="O(1)"))


class TestAbandon:
    def test_abandoning_closes_the_attempt_without_a_verdict(self) -> None:
        attempt = an_attempt()

        attempt.abandon(at=at(5))

        assert attempt.status is AttemptStatus.ABANDONED
        assert attempt.finished_at == at(5)
        assert attempt.verdict is None

    def test_an_abandoned_attempt_accepts_nothing_further(self) -> None:
        attempt = an_attempt()
        attempt.abandon(at=at(5))

        with pytest.raises(AttemptStateError, match="abandoned"):
            attempt.record_command(["git", "log"], OK, at=at(6))
        with pytest.raises(AttemptStateError):
            attempt.complete(a_verdict(), at=at(6))

    def test_a_completed_attempt_cannot_be_abandoned(self) -> None:
        attempt = an_attempt()
        attempt.complete(a_verdict(), at=at(10))

        with pytest.raises(AttemptStateError):
            attempt.abandon(at=at(11))


class TestTimestamps:
    def test_the_event_log_may_not_go_backwards(self) -> None:
        attempt = an_attempt()
        attempt.record_command(["git", "log"], OK, at=at(5))

        with pytest.raises(InvalidValueError, match="refusing to record"):
            attempt.record_command(["git", "status"], OK, at=at(4))

    def test_the_first_event_may_not_precede_the_start(self) -> None:
        attempt = an_attempt()

        with pytest.raises(InvalidValueError, match="refusing to record"):
            attempt.record_command(["git", "log"], OK, at=at(-1))

    def test_two_events_at_the_same_instant_are_allowed(self) -> None:
        attempt = an_attempt()

        attempt.record_command(["git", "log"], OK, at=at(1))
        attempt.record_command(["git", "status"], OK, at=at(1))

        assert attempt.command_count == 2

    def test_every_timestamp_must_be_aware(self) -> None:
        attempt = an_attempt()

        with pytest.raises(InvalidValueError, match="timezone-aware"):
            attempt.record_command(
                ["git", "log"],
                OK,
                at=datetime(2026, 9, 30, 10, 0),  # noqa: DTZ001
            )

    def test_elapsed_runs_to_now_while_the_attempt_is_open(self) -> None:
        attempt = an_attempt()

        assert attempt.elapsed(at(7)) == timedelta(minutes=7)

    def test_elapsed_freezes_once_the_attempt_finishes(self) -> None:
        attempt = an_attempt()
        attempt.complete(a_verdict(), at=at(12))

        assert attempt.elapsed(at(99)) == timedelta(minutes=12)

    def test_elapsed_refuses_a_now_before_the_start(self) -> None:
        with pytest.raises(InvalidValueError, match="before it started"):
            an_attempt().elapsed(at(-1))

    def test_elapsed_refuses_a_naive_now(self) -> None:
        with pytest.raises(InvalidValueError, match="timezone-aware"):
            an_attempt().elapsed(datetime(2026, 9, 30, 10, 0))  # noqa: DTZ001


class TestEventLog:
    def test_the_log_is_handed_out_as_a_copy(self) -> None:
        """Returning the internal list would let a use case append an event that
        skipped every guard above.
        """
        attempt = an_attempt()
        attempt.record_command(["git", "log"], OK, at=at(1))
        snapshot = attempt.events

        attempt.record_command(["git", "status"], OK, at=at(2))

        assert isinstance(snapshot, tuple)
        assert len(snapshot) == 1
        assert len(attempt.events) == 2

    def test_the_log_interleaves_every_kind_of_event_in_order(self) -> None:
        attempt = an_attempt()

        attempt.reveal_next_hint(at=at(1))
        attempt.record_command(["git", "log"], OK, at=at(2))
        attempt.save_solution("x = 1", at=at(3))

        assert [type(event).__name__ for event in attempt.events] == [
            "HintRevealed",
            "CommandRun",
            "SolutionSaved",
        ]

    def test_a_command_run_needs_an_argv(self) -> None:
        with pytest.raises(InvalidValueError, match="needs an argv"):
            CommandRun(at=at(1), argv=(), result=OK)

    def test_a_command_result_cannot_have_a_negative_duration(self) -> None:
        with pytest.raises(InvalidValueError):
            CommandResult(exit_code=0, duration_ms=-1)


class TestRestore:
    """Reconstitution: what a repository is allowed to rebuild, and what it is not.

    The reason this is a separate door rather than a replay of the log through the
    public API is in `Attempt.restore`'s own docstring, and the first two tests here
    are that reason as assertions — a stored attempt loads even when it would now be
    *illegal to produce*, because an attempt is graded under the rules it was started
    under. The rest cover what a row can still be wrong about.
    """

    def test_a_round_trip_through_restore_preserves_everything(self) -> None:
        """Every field, in one test, deliberately. A per-field test would pass with
        a `restore` that dropped the one field nobody thought to write a case for.
        """
        original = an_attempt()
        original.reveal_next_hint(at=at(1))
        original.record_command(["git", "log"], OK, at=at(2))
        original.save_solution("x = 1", at=at(3))
        original.declare_complexity(ComplexityClaim(time="O(n)", space="O(1)"))
        original.complete(a_verdict(), at=at(4))

        restored = Attempt.restore(
            attempt_id=original.id,
            exercise_id=original.exercise_id,
            policy=original.policy,
            started_at=original.started_at,
            status=original.status,
            events=original.events,
            finished_at=original.finished_at,
            verdict=original.verdict,
            declared_complexity=original.declared_complexity,
        )

        assert restored.id == original.id
        assert restored.exercise_id == original.exercise_id
        assert restored.policy == original.policy
        assert restored.started_at == original.started_at
        assert restored.status is AttemptStatus.COMPLETED
        assert restored.events == original.events
        assert restored.finished_at == original.finished_at
        assert restored.verdict == original.verdict
        assert restored.declared_complexity == original.declared_complexity
        assert restored.command_count == 1
        assert restored.hints_revealed == 1

    def test_it_loads_a_log_the_current_policy_would_refuse(self) -> None:
        """The case that decides the design.

        An exercise edited down from three commands to one must not make last
        week's attempts unloadable. A `restore` that replayed the log through
        `record_command` would raise here, and the only honest fix would be to
        stop storing the policy — which is the thing that makes the aggregate able
        to enforce anything at all.
        """
        restored = Attempt.restore(
            attempt_id=ATTEMPT_ID,
            exercise_id=EXERCISE_ID,
            policy=a_policy(max_commands=1, allowed_commands=frozenset({"cat"})),
            started_at=STARTED_AT,
            status=AttemptStatus.ACTIVE,
            events=(
                CommandRun(at=at(1), argv=("git", "log"), result=OK),
                CommandRun(at=at(2), argv=("git", "status"), result=OK),
            ),
        )

        assert restored.command_count == 2
        assert restored.remaining_commands == -1

    def test_a_restored_active_attempt_can_still_be_worked_on(self) -> None:
        """Which is the whole point of the attempt table: a second process picks up
        an attempt the first one started and the aggregate behaves normally.
        """
        restored = Attempt.restore(
            attempt_id=ATTEMPT_ID,
            exercise_id=EXERCISE_ID,
            policy=a_policy(),
            started_at=STARTED_AT,
            status=AttemptStatus.ACTIVE,
            events=(CommandRun(at=at(1), argv=("git", "log"), result=OK),),
        )

        restored.record_command(["git", "status"], OK, at=at(2))

        assert restored.command_count == 2

    def test_a_restored_attempt_refuses_an_event_before_its_last_one(self) -> None:
        """The forward-only guard is rebuilt with the log, not reset by it."""
        restored = Attempt.restore(
            attempt_id=ATTEMPT_ID,
            exercise_id=EXERCISE_ID,
            policy=a_policy(),
            started_at=STARTED_AT,
            status=AttemptStatus.ACTIVE,
            events=(CommandRun(at=at(5), argv=("git", "log"), result=OK),),
        )

        with pytest.raises(InvalidValueError, match="already has an event"):
            restored.record_command(["git", "status"], OK, at=at(2))

    def test_an_event_log_out_of_order_is_refused(self) -> None:
        """A row can be wrong about this where the aggregate cannot: the log order
        is `position`, and a query that forgot its `ORDER BY` returns the events in
        whatever order the page cache held them.
        """
        with pytest.raises(InvalidValueError, match="out of order"):
            Attempt.restore(
                attempt_id=ATTEMPT_ID,
                exercise_id=EXERCISE_ID,
                policy=a_policy(),
                started_at=STARTED_AT,
                status=AttemptStatus.ACTIVE,
                events=(
                    CommandRun(at=at(5), argv=("git", "log"), result=OK),
                    CommandRun(at=at(1), argv=("git", "status"), result=OK),
                ),
            )

    def test_an_event_before_the_attempt_started_is_refused(self) -> None:
        with pytest.raises(InvalidValueError, match="out of order"):
            Attempt.restore(
                attempt_id=ATTEMPT_ID,
                exercise_id=EXERCISE_ID,
                policy=a_policy(),
                started_at=STARTED_AT,
                status=AttemptStatus.ACTIVE,
                events=(CommandRun(at=at(-1), argv=("git", "log"), result=OK),),
            )

    def test_a_naive_event_timestamp_is_refused(self) -> None:
        with pytest.raises(InvalidValueError, match=r"events\[0\]"):
            Attempt.restore(
                attempt_id=ATTEMPT_ID,
                exercise_id=EXERCISE_ID,
                policy=a_policy(),
                started_at=STARTED_AT,
                status=AttemptStatus.ACTIVE,
                events=(
                    CommandRun(
                        at=datetime(2026, 9, 30, 9, 1),  # noqa: DTZ001
                        argv=("git", "log"),
                        result=OK,
                    ),
                ),
            )

    @pytest.mark.parametrize(
        ("status", "finished_at"),
        [
            (AttemptStatus.ACTIVE, at(4)),
            (AttemptStatus.COMPLETED, None),
            (AttemptStatus.ABANDONED, None),
        ],
    )
    def test_status_and_finished_at_have_to_agree(
        self, status: AttemptStatus, finished_at: datetime | None
    ) -> None:
        """An attempt is active until it finishes (PLAN.md 8.1), so "active with an
        end time" and "completed with none" are both rows that cannot have been
        produced by the aggregate.
        """
        with pytest.raises(InvalidValueError, match="active until it finishes"):
            Attempt.restore(
                attempt_id=ATTEMPT_ID,
                exercise_id=EXERCISE_ID,
                policy=a_policy(),
                started_at=STARTED_AT,
                status=status,
                finished_at=finished_at,
                verdict=a_verdict() if status is AttemptStatus.COMPLETED else None,
            )

    def test_finishing_before_the_last_event_is_refused(self) -> None:
        with pytest.raises(InvalidValueError, match="before its last event"):
            Attempt.restore(
                attempt_id=ATTEMPT_ID,
                exercise_id=EXERCISE_ID,
                policy=a_policy(),
                started_at=STARTED_AT,
                status=AttemptStatus.ABANDONED,
                events=(CommandRun(at=at(5), argv=("git", "log"), result=OK),),
                finished_at=at(2),
            )

    @pytest.mark.parametrize(
        ("status", "verdict"),
        [
            (AttemptStatus.COMPLETED, None),
            (AttemptStatus.ABANDONED, a_verdict()),
            (AttemptStatus.ACTIVE, a_verdict()),
        ],
    )
    def test_only_a_completed_attempt_carries_a_verdict(
        self, status: AttemptStatus, verdict: Verdict | None
    ) -> None:
        """`complete` is the only thing that attaches one, so every other pairing
        is a mapper bug — most likely a status column read from the wrong row.
        """
        with pytest.raises(InvalidValueError, match="only a completed attempt"):
            Attempt.restore(
                attempt_id=ATTEMPT_ID,
                exercise_id=EXERCISE_ID,
                policy=a_policy(),
                started_at=STARTED_AT,
                status=status,
                finished_at=None if status is AttemptStatus.ACTIVE else at(4),
                verdict=verdict,
            )

    def test_a_restored_completed_attempt_refuses_to_be_completed_again(self) -> None:
        restored = Attempt.restore(
            attempt_id=ATTEMPT_ID,
            exercise_id=EXERCISE_ID,
            policy=a_policy(),
            started_at=STARTED_AT,
            status=AttemptStatus.COMPLETED,
            finished_at=at(4),
            verdict=a_verdict(),
        )

        with pytest.raises(AttemptStateError, match="completed"):
            restored.complete(a_verdict(), at=at(5))


class TestTheInterviewClock:
    """What `deadline`, `remaining` and `overran` answer, and when.

    All three derive from `elapsed()` rather than from `started_at` directly, so
    there is one opinion about when an attempt's clock stops -- which is the
    property that makes a verdict page show the time that was left at
    submission rather than a number still counting down afterwards.
    """

    def test_an_untimed_attempt_has_no_deadline_and_cannot_overrun(self) -> None:
        attempt = an_attempt()

        assert attempt.deadline is None
        assert attempt.remaining(at(999)) is None
        assert attempt.overran(at(999)) is False

    def test_the_deadline_is_the_start_plus_the_policy(self) -> None:
        attempt = an_interview()

        assert attempt.deadline == at(10)

    def test_remaining_counts_down(self) -> None:
        attempt = an_interview()

        assert attempt.remaining(at(0)) == timedelta(minutes=10)
        assert attempt.remaining(at(4)) == timedelta(minutes=6)

    def test_remaining_goes_negative_rather_than_clamping(self) -> None:
        """The overrun is the interesting number once the deadline has passed,
        and clamping it would hide the one fact the solver wants. Presentation
        is the surface's decision, not the aggregate's.
        """
        attempt = an_interview()

        assert attempt.remaining(at(21)) == timedelta(minutes=-11)

    def test_the_deadline_itself_is_not_an_overrun(self) -> None:
        """Strictly greater than, so arriving exactly on time is on time."""
        attempt = an_interview()

        assert attempt.overran(at(10)) is False
        assert attempt.remaining(at(10)) == timedelta()

    def test_a_second_past_the_deadline_is(self) -> None:
        attempt = an_interview()

        assert attempt.overran(at(10) + timedelta(seconds=1)) is True

    def test_both_freeze_when_the_attempt_finishes(self) -> None:
        attempt = an_interview()
        attempt.complete(a_verdict(), at=at(6))

        # Four minutes were left at submission, and still are an hour later.
        assert attempt.remaining(at(6)) == timedelta(minutes=4)
        assert attempt.remaining(at(66)) == timedelta(minutes=4)
        assert attempt.overran(at(66)) is False

    def test_an_attempt_submitted_late_stays_over(self) -> None:
        """Submitting is not refused for being late -- it is recorded as late,
        which is the core bet applied to the clock (ADR 0020).
        """
        attempt = an_interview()
        attempt.complete(a_verdict(), at=at(14))

        assert attempt.overran(at(14)) is True
        assert attempt.remaining(at(14)) == timedelta(minutes=-4)
        assert attempt.status is AttemptStatus.COMPLETED


class TestHintsUnderInterviewMode:
    def test_a_hint_is_refused_and_the_refusal_says_why(self) -> None:
        """Withholding the hints needed no new code path -- an empty tuple makes
        the existing guard fire -- but the message it fired with said "this
        exercise has 0", which is false. The exercise has two.
        """
        attempt = an_interview()

        with pytest.raises(PolicyViolationError, match="interview mode withholds"):
            attempt.reveal_next_hint(at=at(1))

        assert attempt.hints_revealed == 0
        assert attempt.remaining_hints == 0

    def test_a_practice_attempt_out_of_hints_still_says_so_instead(self) -> None:
        """The old sentence is still the right one when it is true."""
        attempt = an_attempt()
        attempt.reveal_next_hint(at=at(1))
        attempt.reveal_next_hint(at=at(2))

        with pytest.raises(PolicyViolationError, match="no hints left"):
            attempt.reveal_next_hint(at=at(3))


def an_interview() -> Attempt:
    """An attempt opened under interview rules: ten minutes, no hints."""
    return an_attempt(
        a_policy(mode=AttemptMode.INTERVIEW, deadline_seconds=600, hints=())
    )


def a_scenario_exercise() -> Exercise:
    return Exercise(
        id=EXERCISE_ID,
        kind=ExerciseKind.GIT_SCENARIO,
        title="Undo a commit that is already on origin",
        prompt="You pushed the most recent commit to origin/main.",
        difficulty=Difficulty.MEDIUM,
        tags=(tag("history"),),
        estimated_minutes=10,
        hints=HINTS,
        notes="Why revert and not reset.",
        spec=GitScenarioSpec(
            fixture="fixture.sh",
            reference="solution.cmds",
            checks=(
                CheckSpec(
                    id="content-restored",
                    label="tree matches",
                    severity=Severity.REQUIRED,
                    assertion="tree_equals",
                ),
            ),
            allowed_commands=frozenset({"git", "cat"}),
        ),
    )


def a_kata_exercise() -> Exercise:
    return Exercise(
        id=ExerciseId("katas/two-sum"),
        kind=ExerciseKind.KATA,
        title="Two Sum",
        prompt="Return the indices of the two numbers that add up to the target.",
        difficulty=Difficulty.EASY,
        tags=(tag("arrays"),),
        estimated_minutes=15,
        hints=HINTS,
        notes="A dict of value -> index.",
        spec=KataSpec(
            language="python",
            stub="stub.py",
            tests="tests.py",
            reference="solution.py",
        ),
    )
