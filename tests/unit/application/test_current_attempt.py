"""Which attempt "this" is: one use case writes it and another reads it back.

ADR 0026, and one file for both because neither means anything alone -- every
assertion worth making is of the form *after this was marked and that happened,
a tutor is shown the other*.

**The first half is the rule, one case per way it can come out.** Each of them
is a state a solver gets into without trying, and the two that matter most were
both found by something other than a test: the report that started this
(several open, and it asked every time) and the review that followed (one left
open, and it answered with the wrong one).

**The second half is who is allowed to move the mark**, which is as much a
part of the decision as the rule. Starting and resuming do not, because
`practice solve` starts and `practice submit` resumes; a finished attempt
cannot take it; a page being loaded does not (`test_open_workbench.py`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.persistence import InMemoryAttemptRepository
from practice.application.errors import AttemptNotFoundError
from practice.domain.errors import AttemptStateError
from practice.domain.ids import AttemptId, ExerciseId
from tests.unit.application.helpers import (
    a_find_current_attempt,
    a_list_open_attempts,
    a_mark_current_attempt,
    a_resume_attempt,
    a_start_attempt,
    a_submit_solution,
    an_abandon_attempt,
    an_environment,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.domain.attempt import Attempt
    from tests.unit.application.helpers import World

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
MISSING = AttemptId.parse("deadbeef-0000-4000-8000-000000000000")


def start(
    world: World, exercise: ExerciseId = KATA, *, mark: bool = False
) -> AttemptId:
    """Start an attempt, and say so if the solver is to be looking at it."""
    attempt_id = a_start_attempt(world)(exercise).attempt.id
    if mark:
        a_mark_current_attempt(world)(attempt_id)
    return attempt_id


def current(world: World) -> AttemptId | None:
    """The rule, called the way its three callers call it: handed the open
    attempts they have just listed.
    """
    return a_find_current_attempt(world)(a_list_open_attempts(world)())


# --- the rule ----------------------------------------------------------------


def test_with_nothing_open_and_nothing_marked_there_is_no_current_attempt() -> None:
    assert current(an_environment()) is None


def test_the_only_open_attempt_is_current_without_being_marked() -> None:
    """Nothing to choose between -- and every database written before the mark
    existed, which must go on answering as it did.
    """
    world = an_environment()
    only = start(world)

    assert current(world) == only


def test_several_open_and_none_marked_is_no_answer_rather_than_a_guess() -> None:
    """What is left of ADR 0024's refusal. The newest would be the obvious
    pick and is the one a kata makes wrong: nothing is recorded between start
    and submit, so "newest" says nothing about which one is being worked on.
    """
    world = an_environment()
    start(world)
    start(world, SCENARIO)

    assert current(world) is None


def test_the_marked_attempt_is_current_among_several() -> None:
    """The report: one exercise left unfinished, and every question about the
    other was answered with *which attempt?*.
    """
    world = an_environment()
    older = start(world, mark=True)
    start(world, SCENARIO)

    assert current(world) == older


def test_marking_another_attempt_moves_it() -> None:
    world = an_environment()
    first = start(world, mark=True)
    second = start(world, SCENARIO, mark=True)
    assert current(world) == second

    a_mark_current_attempt(world)(first)

    assert current(world) == first


def test_an_attempt_submitted_while_marked_is_still_the_current_one() -> None:
    """**The review's first finding, and the path everybody walks.** One
    attempt left unfinished, a second worked and submitted, and the question is
    *what did I get wrong?* The only open attempt is the stale one; a rule that
    looked at what was open handed that over, with the other's verdict on
    screen.
    """
    world = an_environment()
    stale = start(world, SCENARIO)
    worked = start(world, mark=True)

    a_submit_solution(world)(worked, source="def two_sum(): ...")

    assert current(world) == worked
    assert current(world) != stale


def test_a_submitted_attempt_stays_current_with_several_others_open() -> None:
    world = an_environment()
    start(world, SCENARIO)
    start(world, SCENARIO)
    worked = start(world, mark=True)

    a_submit_solution(world)(worked, source="def two_sum(): ...")

    assert current(world) == worked


def test_turning_to_an_open_attempt_takes_the_mark_back_from_a_finished_one() -> None:
    """The other half of letting a finished attempt keep it: the verdict page
    is current only until the solver is in front of something else.
    """
    world = an_environment()
    other = start(world, SCENARIO)
    worked = start(world, mark=True)
    a_submit_solution(world)(worked, source="def two_sum(): ...")

    a_mark_current_attempt(world)(other)

    assert current(world) == other


def test_an_abandoned_attempt_is_nobodys_current_one() -> None:
    """Abandoning is being done with an attempt without wanting it graded:
    there is no verdict to go over. With several still open and the solver
    having said nothing about them since, the answer is to ask.
    """
    world = an_environment()
    start(world)
    start(world, SCENARIO)
    given_up = start(world, mark=True)

    an_abandon_attempt(world)(given_up)

    assert current(world) is None


def test_after_abandoning_the_marked_attempt_the_only_one_left_is_current() -> None:
    world = an_environment()
    left = start(world, SCENARIO)
    given_up = start(world, mark=True)

    an_abandon_attempt(world)(given_up)

    assert current(world) == left


def test_a_mark_whose_attempt_is_gone_is_read_as_no_mark() -> None:
    """Only a row deleted by hand gets here, and there is no foreign key to
    stop it (`0004_current_attempt.sql`). It must not be an id that every tool
    then fails to load.
    """
    world = an_environment()
    only = start(world)
    world.attempts.mark_current(MISSING)

    assert current(world) == only


class CountingAttempts(InMemoryAttemptRepository):
    """The in-memory store, noting each time attempts are loaded from it."""

    __slots__ = ("loads",)

    def __init__(self) -> None:
        super().__init__()
        self.loads: list[str] = []

    def get(self, attempt_id: AttemptId) -> Attempt | None:
        self.loads.append("get")
        return super().get(attempt_id)

    def active(self) -> Sequence[Attempt]:
        self.loads.append("active")
        return super().active()


def test_it_loads_no_attempt_when_the_marked_one_is_in_the_list_it_was_handed() -> None:
    """The second review's last finding. Every caller has just listed the open
    attempts, and the version that fetched its own loaded them again -- twice
    over for a listing. Handed the list, the ordinary case reads one id.
    """
    world = an_environment()
    world.attempts = CountingAttempts()
    start(world, SCENARIO)
    working_on = start(world, mark=True)
    still_open = a_list_open_attempts(world)()
    world.attempts.loads.clear()

    assert a_find_current_attempt(world)(still_open) == working_on
    assert world.attempts.loads == []


def test_it_loads_one_attempt_when_the_mark_names_something_no_longer_open() -> None:
    """The one read it cannot do without: whether the attempt that left the
    list was submitted or abandoned is the whole of the rule at that point.
    """
    world = an_environment()
    world.attempts = CountingAttempts()
    start(world, SCENARIO)
    worked = start(world, mark=True)
    a_submit_solution(world)(worked, source="def two_sum(): ...")
    still_open = a_list_open_attempts(world)()
    world.attempts.loads.clear()

    assert a_find_current_attempt(world)(still_open) == worked
    assert world.attempts.loads == ["get"]


# --- who may move the mark ---------------------------------------------------


def test_starting_an_attempt_does_not_move_the_mark() -> None:
    """Where the mark was first written, and the review's third finding.
    `practice solve` starts an attempt and finishes it in the same breath; it
    took the mark from the attempt on screen for one nobody was looking at.
    A surface that puts an attempt in front of a person says so itself.
    """
    world = an_environment()
    working_on = start(world, mark=True)

    start(world, SCENARIO)

    assert world.attempts.current() == working_on


def test_resuming_an_attempt_does_not_move_the_mark() -> None:
    """`practice submit` loads through `ResumeAttempt` on its way to closing
    the attempt. That is not the solver turning to it.
    """
    world = an_environment()
    other = start(world, SCENARIO)
    working_on = start(world, mark=True)

    a_resume_attempt(world)(other)

    assert world.attempts.current() == working_on


def test_a_finished_attempt_cannot_take_the_mark() -> None:
    """A tab left open across a submission goes on reporting that it came to
    the front. It keeps the mark if it had it; it cannot take it back from the
    attempt being worked on.
    """
    world = an_environment()
    finished = start(world)
    an_abandon_attempt(world)(finished)
    working_on = start(world, SCENARIO, mark=True)

    with pytest.raises(AttemptStateError, match="it is abandoned"):
        a_mark_current_attempt(world)(finished)

    assert world.attempts.current() == working_on


def test_marking_an_attempt_nobody_saved_is_refused() -> None:
    world = an_environment()

    with pytest.raises(AttemptNotFoundError, match="no attempt with id"):
        a_mark_current_attempt(world)(MISSING)

    assert world.attempts.current() is None


def test_marking_writes_nothing_to_the_attempt() -> None:
    """Beside the attempts, not on one: no event, because turning to an attempt
    is not something the solver did *in the exercise* and the advisory checks
    read that log (§6.3).
    """
    world = an_environment()
    attempt_id = start(world, mark=True)

    stored = world.attempts.get(attempt_id)

    assert stored is not None
    assert stored.events == ()
    assert stored.is_active
