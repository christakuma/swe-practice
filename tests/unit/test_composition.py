"""The wiring point: does the graph it builds satisfy the ports it claims to?

As in `test_ports.py`, **mypy is the real enforcement** — `Services` annotates
its fields with the port protocols, so an adapter that drifts out of shape fails
the type check, and nothing else would catch it because an adapter never
subclasses its port.

What the asserts add is the part a type checker cannot see: that building the
graph writes nothing to disk, that the kata grader is registered and the
scenario grader deliberately is not, and that the overrides the test suite
depends on actually reach the adapters they are meant to configure.

A unit test rather than an integration one, because nothing here runs: every
adapter stores the paths it was given and reads them when it is used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.adapters.sandbox import SubprocessSandboxProvisioner
from practice.application.use_cases import StartAttempt, SubmitSolution
from practice.composition import Services, build_services
from practice.config import content_root
from practice.domain.exercise import ExerciseKind
from practice.domain.ids import ExerciseId
from tests.fakes import FakeClock

if TYPE_CHECKING:
    from pathlib import Path


def test_the_real_graph_satisfies_every_port() -> None:
    """The annotation on each `Services` field is the assertion; this builds the
    graph so that a failure is a test failure rather than only a mypy one.
    """
    services: Services = build_services()

    assert services.content.get(ExerciseId("katas/two-sum")) is not None
    assert isinstance(services.start_attempt, StartAttempt)
    assert isinstance(services.submit_solution, SubmitSolution)


def test_building_the_graph_writes_nothing_to_disk(tmp_path: Path) -> None:
    """Building must not create the cache directory as a side effect, or
    `practice validate` would leave one behind on a machine that has never run
    an attempt.
    """
    workspaces = tmp_path / "ws"

    build_services(workspaces=workspaces)

    assert not workspaces.exists()


def test_every_exercise_kind_has_a_grader() -> None:
    """As of Phase 5, both of them. Asserted against the enum rather than against a
    literal pair, so adding a third kind without a grader fails here -- which is the
    one place that can notice before a solver does.
    """
    graders = build_services().graders

    assert set(graders.graders) == set(ExerciseKind)


def test_the_content_root_override_reaches_both_adapters() -> None:
    """One argument, two readers: the repository loads exercises from it and the
    provisioner copies fixtures out of it. A root that reached only one of them
    would make the content suite load from a temp library and provision from the
    real one.
    """
    library = content_root()

    services = build_services(content=library)

    assert services.content.get(ExerciseId("katas/two-sum")) is not None
    # Narrowed to the concrete adapter deliberately: `directory_for` is not on
    # the port, and this test is about what the wiring point built rather than
    # about what a use case can see.
    assert isinstance(services.provisioner, SubprocessSandboxProvisioner)
    assert services.provisioner.directory_for(ExerciseId("katas/two-sum")) == (
        library / "katas" / "two-sum"
    )


def test_an_injected_clock_is_the_one_the_use_cases_use() -> None:
    clock = FakeClock()

    services = build_services(clock=clock)

    assert services.clock is clock
    assert services.start_attempt.clock is clock
    assert services.submit_solution.clock is clock


def test_the_use_cases_are_wired_to_the_same_objects() -> None:
    """Both use cases share the attempt store, which is the whole reason
    `SubmitSolution` can find an attempt `StartAttempt` created.
    """
    services = build_services()

    assert services.start_attempt.attempts is services.submit_solution.attempts
    assert services.start_attempt.provisioner is services.submit_solution.provisioner
