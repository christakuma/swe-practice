"""The container dispatcher's three jobs, and the vocabulary staying disjoint."""

from __future__ import annotations

from practice.domain.checks import registry as git_registry
from practice.domain.containers import registry
from practice.domain.drills import registry as drill_registry
from tests.fakes.build import FakeBuildQuery
from tests.unit.domain.containers.helpers import run


def test_a_missing_parameter_is_a_failing_report_not_a_traceback() -> None:
    report = run("path_in_image", FakeBuildQuery())
    assert not report.passed
    assert report.actual is not None
    assert "misconfigured" in report.actual


def test_a_bad_pattern_is_a_failing_report() -> None:
    report = run("runs_as", FakeBuildQuery(), pattern="(")
    assert not report.passed


def test_the_label_is_the_authors() -> None:
    assert run("runs_as", FakeBuildQuery(), pattern="root").label == (
        "The label the author wrote."
    )


def test_the_three_vocabularies_are_disjoint() -> None:
    drills = drill_registry.DRILL_ASSERTIONS
    git = frozenset(
        name
        for name in registry.CONTAINER_ASSERTIONS
        if git_registry.is_registered(name)
    )
    assert not git
    assert not registry.CONTAINER_ASSERTIONS & drills


def test_is_registered() -> None:
    assert registry.is_registered("pid1_matches")
    assert not registry.is_registered("tree_equals")


def test_suggest_offers_a_near_name() -> None:
    assert "pid1_matches" in registry.suggest("pid_matches")


def test_family_of_names_every_kind() -> None:
    assert registry.family_of("service_value") == "container"
    assert registry.family_of("table_matches") == "sql_drill"
    assert registry.family_of("tree_equals") == "git_scenario"
    assert registry.family_of("no_such_thing") is None
