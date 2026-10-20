"""The hidden tests for loading the dashboard's widgets at once.

**Concurrency is checked by who has arrived, not by how long it took.**
`asyncio` is cooperative, so a test can make every service wait at one
`Event` until all four calls have started, and an answer that awaits them one
at a time never starts the second: it fails at `GUARD_SECONDS` rather than
by a stopwatch reading that depends on how loaded the machine is.

**A timeout is checked against a service that never answers**, rather than
one that answers a little late, for the same reason: nothing here depends on
a deadline firing at a precise moment, only on it firing at all. The one
required widget that is slow is slow by twice the budget, and the test asks
only that it is waited for.

Every test runs under `GUARD_SECONDS`, so an answer that waits for ever
fails one test instead of hanging the suite.
"""

from __future__ import annotations

import asyncio

import pytest
from solution import RECOMMENDATIONS_BUDGET, load_dashboard

GUARD_SECONDS = 2.0
WIDGETS = ("profile", "orders", "notifications", "recommendations")


class Services:
    """The four services, each answering at once unless a test says otherwise."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.cancelled: list[str] = []
        self.cancelled_by_the_time_the_page_returned: list[str] = []
        self.everyone_started: asyncio.Event | None = None
        self.never_answers: set[str] = set()
        self.raises: set[str] = set()
        self.delay: dict[str, float] = {}

    async def _call(self, widget: str, user_id: int) -> str:
        self.started.append(widget)
        try:
            if self.everyone_started is not None:
                if len(self.started) == len(WIDGETS):
                    self.everyone_started.set()
                await self.everyone_started.wait()
            if widget in self.never_answers:
                await asyncio.Event().wait()
            if widget in self.delay:
                await asyncio.sleep(self.delay[widget])
            if widget in self.raises:
                message = f"{widget} is down"
                raise RuntimeError(message)
        except asyncio.CancelledError:
            self.cancelled.append(widget)
            raise
        return f"{widget} for {user_id}"

    async def profile(self, user_id: int) -> str:
        return await self._call("profile", user_id)

    async def orders(self, user_id: int) -> str:
        return await self._call("orders", user_id)

    async def notifications(self, user_id: int) -> str:
        return await self._call("notifications", user_id)

    async def recommendations(self, user_id: int) -> str:
        return await self._call("recommendations", user_id)


def load(services: Services) -> dict[str, str | None]:
    async def guarded() -> dict[str, str | None]:
        page = await asyncio.wait_for(load_dashboard(7, services), GUARD_SECONDS)
        # Two turns of the loop, so a cancellation that was requested and not
        # awaited has been delivered. Recorded here rather than after `run`
        # returns, because `asyncio.run` cancels every task still pending as
        # it closes, and would cancel a call the answer had left running.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        services.cancelled_by_the_time_the_page_returned = list(services.cancelled)
        return page

    return asyncio.run(guarded())


def test_the_page_has_every_widget() -> None:
    """With every service answering, the page has all four widgets."""
    page = load(Services())
    assert page == {widget: f"{widget} for 7" for widget in WIDGETS}


def test_the_four_calls_are_in_flight_at_once() -> None:
    """All four calls are started before any of them has to answer."""
    services = Services()

    async def run() -> dict[str, str | None]:
        services.everyone_started = asyncio.Event()
        return await asyncio.wait_for(load_dashboard(7, services), GUARD_SECONDS)

    page = asyncio.run(run())
    assert sorted(services.started) == sorted(WIDGETS)
    assert page["orders"] == "orders for 7"


def test_recommendations_that_answer_in_time_are_shown() -> None:
    """Recommendations that answer inside the budget are on the page."""
    page = load(Services())
    assert page["recommendations"] == "recommendations for 7"


def test_silent_recommendations_are_left_out() -> None:
    """Recommendations that never answer are None, and the rest of the page is there."""
    services = Services()
    services.never_answers.add("recommendations")
    page = load(services)
    assert page["recommendations"] is None
    assert page["profile"] == "profile for 7"


def test_the_abandoned_call_is_cancelled() -> None:
    """A recommendations call past its budget is cancelled, not left running."""
    services = Services()
    services.never_answers.add("recommendations")
    load(services)
    assert services.cancelled_by_the_time_the_page_returned == ["recommendations"]


def test_failing_recommendations_are_left_out() -> None:
    """Recommendations that raise are None, and the page still loads."""
    services = Services()
    services.raises.add("recommendations")
    page = load(services)
    assert page["recommendations"] is None
    assert page["notifications"] == "notifications for 7"


def test_a_slow_required_widget_is_waited_for() -> None:
    """Orders that take twice the budget are still on the page."""
    services = Services()
    services.delay["orders"] = 2 * RECOMMENDATIONS_BUDGET
    page = load(services)
    assert page["orders"] == "orders for 7"


def _messages(error: BaseException) -> list[str]:
    """The error's message, or every message inside it if it is a group.

    A `TaskGroup` raises the error it caught inside an `ExceptionGroup`, and
    `gather` raises it bare. Both are the error reaching the caller, so both
    pass.
    """
    if isinstance(error, BaseExceptionGroup):
        return [message for inner in error.exceptions for message in _messages(inner)]
    return [str(error)]


def test_a_failing_required_widget_fails_the_page() -> None:
    """If orders raises, the dashboard raises rather than drawing a page without it."""
    services = Services()
    services.raises.add("orders")
    with pytest.raises(Exception) as raised:  # noqa: PT011 -- a group is fine too
        load(services)
    assert "orders is down" in _messages(raised.value)
