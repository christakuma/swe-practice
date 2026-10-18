"""`service_value` and `service_mount` over a normalised compose service."""

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


BIND = {"type": "bind", "source": ".", "target": "/app"}
ANONYMOUS = {"type": "volume", "target": "/app/node_modules"}
WEB = FakeBuildQuery(services={"web": {"volumes": [BIND, ANONYMOUS]}, "db": {}})


class TestServiceMount:
    def test_a_volume_at_the_target_passes(self) -> None:
        report = run(
            "service_mount",
            WEB,
            service="web",
            target="/app/node_modules",
            type="volume",
        )
        assert report.passed
        assert report.expected == "web mounts a volume at /app/node_modules"
        assert report.actual == (
            "web mounts bind . at /app; volume (anonymous) at /app/node_modules"
        )

    def test_the_wrong_type_at_the_target_fails(self) -> None:
        """A bind of `./node_modules` hides the image's copy; a volume copies it."""
        stack = FakeBuildQuery(
            services={
                "web": {
                    "volumes": [
                        BIND,
                        {
                            "type": "bind",
                            "source": "./node_modules",
                            "target": "/app/node_modules",
                        },
                    ]
                }
            }
        )
        report = run(
            "service_mount",
            stack,
            service="web",
            target="/app/node_modules",
            type="volume",
        )
        assert not report.passed

    def test_a_trailing_slash_is_the_same_target(self) -> None:
        assert run(
            "service_mount", WEB, service="web", target="/app/", type="bind"
        ).passed

    def test_a_service_that_mounts_nothing_says_so(self) -> None:
        report = run("service_mount", WEB, service="db", target="/app", type="bind")
        assert not report.passed
        assert report.actual == "db mounts nothing"

    def test_an_undeclared_service_names_the_ones_there_are(self) -> None:
        report = run("service_mount", WEB, service="api", target="/", type="bind")
        assert report.actual == "<no service 'api'; declared: db, web>"

    def test_a_file_with_no_services_says_none(self) -> None:
        report = run(
            "service_mount", FakeBuildQuery(), service="web", target="/", type="bind"
        )
        assert report.actual == "<no service 'web'; declared: none>"

    def test_an_unreadable_file_says_so(self) -> None:
        report = run(
            "service_mount",
            FakeBuildQuery(error="bad"),
            service="web",
            target="/app",
            type="bind",
        )
        assert report.actual == "<no definition could be read>"

    def test_an_entry_that_is_not_a_mapping_is_not_a_mount(self) -> None:
        """Unreachable through the normaliser, which refuses one; held anyway."""
        stack = FakeBuildQuery(services={"web": {"volumes": ["junk"]}})
        report = run("service_mount", stack, service="web", target="/", type="bind")
        assert report.actual == "web mounts nothing"

    def test_negated_it_rules_a_mount_out(self) -> None:
        report = run(
            "service_mount",
            WEB,
            service="web",
            target="/app/node_modules",
            type="bind",
            negated=True,
        )
        assert report.passed


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
