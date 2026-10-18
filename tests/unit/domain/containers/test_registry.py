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


def test_a_negated_check_does_not_pass_on_an_unreadable_definition() -> None:
    """Every assertion fails on nothing, and `not:` used to make that a pass.

    A typo'd Dockerfile showed `.env is in no layer` in green beside the failed
    `definition-parsed`. A check that read nothing has ruled nothing out.
    """
    broken = FakeBuildQuery(error="line 2: unknown instruction 'COPPY'")
    cases: list[tuple[str, dict[str, str]]] = [
        ("path_in_image", {"path": ".env"}),
        ("pid1_matches", {"pattern": "sh$"}),
        ("runs_as", {"pattern": "^root$"}),
        ("instruction_matches", {"pattern": "^STOPSIGNAL"}),
        ("service_value", {"service": "api", "key": "network_mode", "pattern": "."}),
    ]
    for assertion, params in cases:
        report = run(assertion, broken, negated=True, **params)
        assert not report.passed, assertion
        assert (report.expected or "").startswith("not ")


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
