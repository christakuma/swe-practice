"""The hidden tests for the payments retry policy.

Nothing here sleeps. `sleep` records what it was asked to wait, and `rng`
records the bounds it was asked for and answers with a draw the test chose, so
the policy's timing is checked as numbers rather than measured as time --
which is the only way a test of backoff can be both exact and fast.

`Script` is the operation: a list of outcomes, consumed one per call, where
an exception is raised and anything else is returned.
"""

from __future__ import annotations

import pytest
from solution import Unavailable, call_with_retries


class BadRequest(Exception):
    """A failure that is not worth retrying: it will fail the same way again."""


class Script:
    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self) -> object:
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class Sleeps(list[float]):
    def __call__(self, seconds: float) -> None:
        self.append(seconds)


class Rng:
    """Draws `fraction` of the way between the bounds, and records them."""

    def __init__(self, fraction: float = 0.5) -> None:
        self.fraction = fraction
        self.bounds: list[tuple[float, float]] = []

    def uniform(self, low: float, high: float) -> float:
        self.bounds.append((low, high))
        return low + (high - low) * self.fraction


def test_returns_the_first_success() -> None:
    """A call that succeeds first time is returned, with no wait."""
    operation, sleep = Script("paid"), Sleeps()
    assert call_with_retries(operation, sleep=sleep, rng=Rng()) == "paid"
    assert operation.calls == 1
    assert sleep == []


def test_retries_unavailable_until_it_succeeds() -> None:
    """Unavailable is retried, and the first success is returned."""
    operation = Script(Unavailable(), Unavailable(), "paid")
    sleep = Sleeps()
    assert call_with_retries(operation, sleep=sleep, rng=Rng()) == "paid"
    assert operation.calls == 3
    assert len(sleep) == 2


def test_gives_up_after_four_attempts() -> None:
    """After four attempts it raises the last Unavailable, with no wait after it."""
    last = Unavailable("fourth")
    operation = Script(Unavailable(), Unavailable(), Unavailable(), last)
    sleep = Sleeps()
    with pytest.raises(Unavailable) as raised:
        call_with_retries(operation, sleep=sleep, rng=Rng())
    assert raised.value is last
    assert operation.calls == 4
    assert len(sleep) == 3


def test_other_errors_are_not_retried() -> None:
    """Any other error is raised at once, without a retry or a wait."""
    operation, sleep = Script(BadRequest(), "paid"), Sleeps()
    with pytest.raises(BadRequest):
        call_with_retries(operation, sleep=sleep, rng=Rng())
    assert operation.calls == 1
    assert sleep == []


def test_an_error_after_a_retry_is_not_retried_either() -> None:
    """A different error on a retry ends the retrying there."""
    operation = Script(Unavailable(), BadRequest(), "paid")
    with pytest.raises(BadRequest):
        call_with_retries(operation, sleep=Sleeps(), rng=Rng())
    assert operation.calls == 2


def test_the_ceilings_double_from_a_fifth_of_a_second() -> None:
    """The three waits are drawn between 0 and 0.2, 0.4 and 0.8 seconds."""
    operation = Script(Unavailable(), Unavailable(), Unavailable(), "paid")
    rng = Rng()
    call_with_retries(operation, sleep=Sleeps(), rng=rng)
    flat = [bound for pair in rng.bounds for bound in pair]
    assert flat == pytest.approx([0, 0.2, 0, 0.4, 0, 0.8]), rng.bounds


def test_each_wait_is_the_random_draw() -> None:
    """Each wait is the random draw itself, not its ceiling."""
    operation = Script(Unavailable(), Unavailable(), Unavailable(), "paid")
    sleep = Sleeps()
    call_with_retries(operation, sleep=sleep, rng=Rng(fraction=0.25))
    assert sleep == pytest.approx([0.05, 0.1, 0.2])
