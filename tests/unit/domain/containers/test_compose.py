"""`service_value` over a normalised compose service, and how values are rendered."""

from __future__ import annotations

import pytest

from practice.domain.containers.compose import render
from tests.fakes.build import FakeBuildQuery
from tests.unit.domain.containers.helpers import run

API = {
    "environment": {"DATABASE_URL": "postgres://app:app@db:5432/app"},
    "depends_on": {"db": {"condition": "service_started"}},
}
DB = {"healthcheck": {"test": ["CMD", "pg_isready", "-U", "app"]}}
STACK = FakeBuildQuery(services={"api": API, "db": DB})


def test_a_dotted_key_reaches_an_environment_variable() -> None:
    report = run(
        "service_value",
        STACK,
        service="api",
        key="environment.DATABASE_URL",
        pattern="@db:5432/",
    )
    assert report.passed


def test_the_short_depends_on_does_not_wait_for_health() -> None:
    report = run(
        "service_value",
        STACK,
        service="api",
        key="depends_on.db.condition",
        pattern="^service_healthy$",
    )
    assert not report.passed
    assert report.actual == "depends_on.db.condition is 'service_started'"


def test_a_list_healthcheck_reads_as_a_command_line() -> None:
    report = run(
        "service_value",
        STACK,
        service="db",
        key="healthcheck.test",
        pattern="pg_isready",
    )
    assert report.passed


def test_an_unset_key_fails_so_negation_means_absent() -> None:
    plain = run("service_value", STACK, service="api", key="network_mode", pattern=".")
    assert not plain.passed
    assert plain.actual == "network_mode is <not set>"
    negated = run(
        "service_value",
        STACK,
        service="api",
        key="network_mode",
        pattern=".",
        negated=True,
    )
    assert negated.passed


def test_a_key_through_a_scalar_is_unset() -> None:
    report = run(
        "service_value",
        STACK,
        service="api",
        key="environment.DATABASE_URL.host",
        pattern=".",
    )
    assert not report.passed


def test_an_undeclared_service_names_the_ones_there_are() -> None:
    report = run("service_value", STACK, service="web", key="image", pattern=".")
    assert report.actual == "<no service 'web'; declared: api, db>"


def test_a_file_with_no_services_says_none() -> None:
    report = run("service_value", FakeBuildQuery(), service="web", key="a", pattern=".")
    assert report.actual == "<no service 'web'; declared: none>"


def test_an_unreadable_file_says_so() -> None:
    report = run(
        "service_value",
        FakeBuildQuery(error="bad"),
        service="api",
        key="a",
        pattern=".",
    )
    assert report.actual == "<no definition could be read>"


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (True, "true"),
        (False, "false"),
        (5432, "5432"),
        ("db", "db"),
        (["CMD", "pg_isready"], "CMD pg_isready"),
        ({"a": 1, "b": [2, 3]}, "a=1 b=2 3"),
    ],
)
def test_render(value: object, text: str) -> None:
    assert render(value) == text
