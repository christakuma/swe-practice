"""A client over the real app, wired to fakes.

**Fakes rather than real adapters, for the same reason the application tests use
them**: what a route gets wrong is which use case it calls, what it hands the
template, and what it does with an error — none of which needs a git process or a
temp directory to be wrong in. The one test that does need real adapters is the
end-to-end one in `tests/e2e/`, which is where a slow test belongs.

**Every request carries the headers a browser would send.** `TestClient` sends
none by default, and `SameOriginMiddleware` refuses a mutating request that cannot
prove its origin — so a fixture that did not set them would make every POST test
a test of the guard. Setting them here means the guard's own tests are the ones
that leave them off, which is the right way round: the browser contract is stated
in one place and the security tests are explicit about violating it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from practice.adapters.persistence import (
    InMemoryAttemptRepository,
    InMemoryReviewRepository,
)
from practice.application.registry import GraderRegistry
from practice.composition import Services
from practice.domain.exercise import ExerciseKind
from practice.interface.web import create_app
from tests.fakes import (
    BuilderRepoQueryFactory,
    FakeClock,
    FakeContentRepository,
    FakeEditorLauncher,
    FakeFileWatcher,
    FakeProvisioner,
    FixedScheduler,
    SequentialIdGenerator,
    a_kata,
    a_repo,
    a_scenario,
)
from tests.unit.application.helpers import RecordingGrader

if TYPE_CHECKING:
    from collections.abc import Iterator

    from practice.domain.exercise import Exercise
    from practice.domain.ports import Scheduler

#: The origin the client speaks as, and the base url it requests. `TestClient`
#: defaults to `http://testserver`, which `SameOriginMiddleware` refuses on the
#: `Host` check -- correctly, since `testserver` is not a loopback name. Rather
#: than loosen the guard for the convenience of the test client, the test client
#: pretends to be a browser pointed at the real server, which is what it is
#: standing in for.
ORIGIN = "http://127.0.0.1"

#: What a browser sends on a same-origin HTMX request: `fetch` sets `Origin` for
#: every non-GET, and the browser sets `Sec-Fetch-Site` on everything.
BROWSER_HEADERS = {"origin": ORIGIN, "sec-fetch-site": "same-origin"}


class Wiring:
    """The fakes behind a client, reachable so a test can assert on them.

    A small class rather than a tuple, because a test wants two or three of these
    by name — `wiring.attempts` to see what was saved, `wiring.provisioner` to see
    what was built — and positional unpacking of five things is unreadable.
    """

    def __init__(
        self,
        *,
        exercises: tuple[Exercise, ...],
        grader: RecordingGrader,
        scheduler: Scheduler | None = None,
    ) -> None:
        self.content = FakeContentRepository(exercises)
        self.attempts = InMemoryAttemptRepository()
        self.reviews = InMemoryReviewRepository()
        self.provisioner = FakeProvisioner()
        self.clock = FakeClock()
        #: The *port*, not the double, because a test may substitute a real
        #: scheduler for it -- the schedule panel shows different numbers
        #: depending on which one moved the card (ADR 0018), and only a real one
        #: writes a memory state. `recording_scheduler` is how a test that wants
        #: the double's record of what it was handed asks for it.
        #:
        #: The default records the grade rather than doing SM-2's arithmetic, so
        #: a web test asserts on what the page sent and not on an interval it
        #: would have to keep in step with the scheduler.
        self.scheduler: Scheduler = (
            scheduler if scheduler is not None else FixedScheduler()
        )
        self.ids = SequentialIdGenerator(start=0)
        #: The editor the reveal endpoint drives. A fake, because the real one
        #: starts a GUI program -- and a web test that opened VS Code would be a
        #: web test nobody runs twice.
        self.editor = FakeEditorLauncher()
        #: Ctrl+S, scripted. A web test arranges the saves it wants and then
        #: drains the stream, rather than writing a file and waiting.
        self.watcher = FakeFileWatcher()
        self.grader = grader
        #: The repository the state panel and the commit graph are drawn from. A
        #: *builder* rather than a built query, so a test can start an attempt and
        #: then say what its repository looks like -- which is the order a web test
        #: reads in, and the order the real factory allows because it builds one
        #: query per call.
        self.repo = a_repo()

    @property
    def services(self) -> Services:
        """Shaped exactly like what `build_services` returns, over fakes.

        The real `Services` rather than a look-alike: it is a frozen dataclass of
        ports, so a test that built its own would be free to disagree with the
        composition root about what a route is given.
        """
        return Services(
            content=self.content,
            attempts=self.attempts,
            reviews=self.reviews,
            provisioner=self.provisioner,
            graders=GraderRegistry(
                graders={
                    ExerciseKind.KATA: self.grader,
                    ExerciseKind.GIT_SCENARIO: self.grader,
                }
            ),
            clock=self.clock,
            ids=self.ids,
            repo_query=BuilderRepoQueryFactory(self.repo),
            scheduler=self.scheduler,
            editor=self.editor,
            watcher=self.watcher,
        )


def a_wiring(
    grader: RecordingGrader | None = None, scheduler: Scheduler | None = None
) -> Wiring:
    """Both shipped exercise kinds, and a grader that records what it was asked.

    A function as well as a fixture because a test that wants a *failing* verdict
    has to choose the grader before the client is built -- the same shape
    `an_environment(grader=...)` takes in the application tests, and for the same
    reason: a shared environment mutated after the fact would make every test in
    the file depend on the order they ran in.

    `scheduler` arrives on the same terms, and the same reasoning decided it: a
    test that wants a real scheduler chooses it here rather than reassigning the
    attribute afterwards.
    """
    return Wiring(
        exercises=(a_kata(), a_scenario()),
        grader=grader if grader is not None else RecordingGrader(),
        scheduler=scheduler,
    )


def recording_scheduler(wiring: Wiring) -> FixedScheduler:
    """The double, narrowed, for the tests that assert on what it was handed.

    `Wiring.scheduler` is typed as the port because a test may put a real
    scheduler there, so the double's recording API is not reachable from the
    attribute alone. One door rather than a cast per assertion.
    """
    scheduler = wiring.scheduler
    assert isinstance(scheduler, FixedScheduler)
    return scheduler


def client_for(wiring: Wiring) -> TestClient:
    """The app over a wiring a test built itself, speaking as a browser."""
    return TestClient(
        create_app(wiring.services), base_url=ORIGIN, headers=BROWSER_HEADERS
    )


@pytest.fixture
def wiring() -> Wiring:
    return a_wiring()


@pytest.fixture
def client(wiring: Wiring) -> Iterator[TestClient]:
    """The app, driven in-process, speaking as a same-origin browser."""
    with client_for(wiring) as client:
        yield client


@pytest.fixture
def bare_client(wiring: Wiring) -> Iterator[TestClient]:
    """The same app with no browser headers at all.

    For the security tests, which are about what happens when a request cannot
    prove where it came from — and which would prove nothing if the fixture had
    already proved it for them.
    """
    with TestClient(create_app(wiring.services), base_url=ORIGIN) as client:
        yield client
