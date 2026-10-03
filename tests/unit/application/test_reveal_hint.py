"""`RevealHint`: one at a time, in order, and recorded.

The use case is thin, and what these pin down is the part that is not: that the
reveal is *persisted* — Phase 9's grade suggestion reads the log, so a reveal the
repository never saw would make a passing attempt look unaided — and that the order
is the aggregate's rather than a parameter anyone can skip ahead with.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from practice.application.errors import AttemptNotFoundError, ExerciseNotFoundError
from practice.domain.attempt import HintRevealed
from practice.domain.errors import AttemptStateError, PolicyViolationError
from practice.domain.exercise import Hint
from practice.domain.ids import AttemptId, ExerciseId
from tests.fakes import a_scenario
from tests.unit.application.helpers import (
    World,
    a_reveal_hint,
    a_start_attempt,
    a_submit_scenario,
    an_environment,
)

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")


#: Three hints, because the shipped fake scenario has one and one cannot show a
#: *progression*. The flagship exercise's own ladder is four, and these are its
#: first three in shape: look, then understand the consequence, then the tool.
HINTS = (
    Hint("Read `build.sh`, then `parser.py`."),
    Hint("Your teammate already has this commit. What happens to them?"),
    Hint("`git revert HEAD`, then push -- no force needed."),
)


def a_world_with_an_attempt(
    exercise: ExerciseId = SCENARIO, *, hints: tuple[Hint, ...] = HINTS
) -> tuple[World, AttemptId]:
    """An attempt at a scenario carrying `hints`, started after they are in place.

    Started *after*, which is the order that matters: `AttemptPolicy` copies the
    list in at construction (§4.3), so an exercise edited afterwards does not reach
    the attempt -- which is itself the subject of the last test in this file.
    """
    world = an_environment()
    if exercise == SCENARIO:
        world.content.replace_with(replace(a_scenario(), hints=hints))
    return world, a_start_attempt(world)(exercise).attempt.id


def test_it_reveals_the_first_hint_first() -> None:
    world, attempt_id = a_world_with_an_attempt()

    revealed = a_reveal_hint(world)(attempt_id)

    del world
    assert revealed.index == 0
    assert revealed.number == 1
    assert revealed.hint == HINTS[0]


def test_successive_calls_walk_the_list_in_order() -> None:
    """No index parameter, and there could not be one: an endpoint that took one is
    an endpoint a solver skips to the answer with, and the progression is the thing
    being recorded.
    """
    world, attempt_id = a_world_with_an_attempt()
    reveal = a_reveal_hint(world)

    assert [reveal(attempt_id).index for _ in range(3)] == [0, 1, 2]


def test_the_reveal_is_persisted_rather_than_only_returned() -> None:
    """Phase 9 reads this log to suggest a grade -- "passed, with three of four
    hints" is a different outcome from "passed" -- so a reveal the repository never
    saw would make an aided attempt look unaided.
    """
    world, attempt_id = a_world_with_an_attempt()

    a_reveal_hint(world)(attempt_id)

    stored = world.attempts.get(attempt_id)
    assert stored is not None
    assert stored.hints_revealed == 1
    assert isinstance(stored.events[-1], HintRevealed)


def test_the_event_records_which_hint_was_shown_and_not_only_that_one_was() -> None:
    world, attempt_id = a_world_with_an_attempt()
    reveal = a_reveal_hint(world)
    reveal(attempt_id)

    revealed = reveal(attempt_id)

    stored = world.attempts.get(attempt_id)
    assert stored is not None
    assert [event.index for event in stored.revealed_hints] == [0, 1]
    assert stored.revealed_hints[-1].hint == revealed.hint


def test_it_counts_down_what_is_left() -> None:
    world, attempt_id = a_world_with_an_attempt()

    revealed = a_reveal_hint(world)(attempt_id)

    assert revealed.remaining == revealed.attempt.policy.hint_count - 1


def test_a_kata_has_hints_too() -> None:
    """Hints belong to the attempt, not to the exercise kind, which is why this is
    one use case and one panel rather than one per kind.
    """
    world, attempt_id = a_world_with_an_attempt(KATA)

    assert a_reveal_hint(world)(attempt_id).number == 1


def test_running_out_is_refused_with_the_count() -> None:
    world, attempt_id = a_world_with_an_attempt()
    reveal = a_reveal_hint(world)
    attempt = world.attempts.get(attempt_id)
    assert attempt is not None
    for _ in range(attempt.policy.hint_count):
        reveal(attempt_id)

    with pytest.raises(PolicyViolationError, match="no hints left"):
        reveal(attempt_id)


def test_a_finished_attempt_is_refused() -> None:
    """A tab left open across a submission, which is the case every mutating path
    in this app has. The guard is the aggregate's, so the sentence is the same one
    a second submission gets.
    """
    world, attempt_id = a_world_with_an_attempt()
    a_submit_scenario(world)(attempt_id)

    with pytest.raises(AttemptStateError, match="reveal a hint"):
        a_reveal_hint(world)(attempt_id)


def test_an_unknown_attempt_is_refused() -> None:
    world = an_environment()

    with pytest.raises(AttemptNotFoundError, match="no attempt with id"):
        a_reveal_hint(world)(AttemptId.parse("00000000-0000-4000-8000-000000000000"))


def test_an_exercise_that_left_the_library_is_refused() -> None:
    world, attempt_id = a_world_with_an_attempt()
    world.content.forget(SCENARIO)

    with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
        a_reveal_hint(world)(attempt_id)


def test_the_hint_comes_from_the_attempt_rather_than_from_the_library_now() -> None:
    """`AttemptPolicy` copied the list in when the attempt started (§4.3).

    An exercise edited mid-attempt would otherwise hand over a hint the solver's
    first two do not lead to, and the log would record a position in a list that no
    longer exists.
    """
    world, attempt_id = a_world_with_an_attempt()
    attempt = world.attempts.get(attempt_id)
    assert attempt is not None
    expected = attempt.policy.hints[0]

    world.content.replace_with(
        replace(a_scenario(), hints=(Hint("A completely different hint."),))
    )

    assert a_reveal_hint(world)(attempt_id).hint == expected
