"""`ContainerSpec`'s invariants, and its clause in `editable_source`.

The content suite only ever builds valid container specs, so the refusals here
are the only thing exercising them. They are domain code, under the coverage
gate, and the gate is what noticed.
"""

from __future__ import annotations

from typing import Any

import pytest

from practice.domain.errors import InvalidValueError
from practice.domain.exercise import (
    CheckSpec,
    ContainerSpec,
    CounterExample,
    EditableSource,
    ExerciseKind,
    editable_source,
)
from practice.domain.verdict import Severity

REQUIRED = CheckSpec(
    id="listens-everywhere",
    label="gunicorn listens on every interface.",
    severity=Severity.REQUIRED,
    assertion="command_matches",
    params={"pattern": "0.0.0.0:8000"},
)
ADVISORY = CheckSpec(
    id="not-root",
    label="Not root.",
    severity=Severity.ADVISORY,
    assertion="runs_as",
    params={"pattern": "^root$"},
    negated=True,
)


def a_spec(**overrides: Any) -> ContainerSpec:
    fields: dict[str, Any] = {
        "context": "context",
        "stub": "Dockerfile",
        "reference": "solution.Dockerfile",
        "checks": (REQUIRED, ADVISORY),
        "counter_examples": (
            CounterExample(
                file="default-bind.Dockerfile",
                expect_failures=frozenset({"listens-everywhere"}),
            ),
        ),
    }
    fields.update(overrides)
    return ContainerSpec(**fields)


@pytest.mark.parametrize("field_name", ["context", "stub", "reference"])
def test_every_name_is_required(field_name: str) -> None:
    with pytest.raises(InvalidValueError, match=f"needs a {field_name}"):
        a_spec(**{field_name: "  "})


@pytest.mark.parametrize("field_name", ["context", "stub", "reference"])
def test_no_name_may_be_a_path(field_name: str) -> None:
    with pytest.raises(InvalidValueError, match="cannot be a path"):
        a_spec(**{field_name: "../escape"})


def test_the_stub_is_named_what_docker_looks_for() -> None:
    """`docker build .` has to work in the workspace without `-f`."""
    with pytest.raises(InvalidValueError, match="docker build"):
        a_spec(stub="stub.Dockerfile")


def test_the_language_follows_from_the_file() -> None:
    assert a_spec().language == "dockerfile"
    assert a_spec(stub="compose.yaml").language == "yaml"


def test_its_kind_checks_and_files() -> None:
    spec = a_spec()
    assert spec.kind is ExerciseKind.CONTAINER
    assert spec.required_checks == (REQUIRED,)
    assert spec.check_ids == frozenset({"listens-everywhere", "not-root"})
    assert spec.referenced_files == (
        "Dockerfile",
        "solution.Dockerfile",
        "default-bind.Dockerfile",
    )


def test_a_check_is_looked_up_by_id() -> None:
    spec = a_spec()
    assert spec.check("not-root") is ADVISORY
    with pytest.raises(InvalidValueError, match="no such check"):
        spec.check("missing")


def test_all_advisory_checks_are_refused() -> None:
    with pytest.raises(InvalidValueError):
        a_spec(checks=(ADVISORY,), counter_examples=())


def test_it_is_edited_in_its_stub() -> None:
    """ADR 0019's prediction, held: the fourth kind is one clause."""
    assert editable_source(a_spec(stub="compose.yaml")) == EditableSource(
        filename="compose.yaml", language="yaml", reference="solution.Dockerfile"
    )
