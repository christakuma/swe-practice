"""What a compose file declares about a service. One assertion, and why only one.

`service_value` takes a dotted key into the service **as the port normalises
it**, so `environment` is always a mapping and `depends_on.db.condition` always
exists once `db` is a dependency, whether the file wrote a list, a mapping or
the long form. That is the whole of what makes this an end-state assertion
rather than a YAML diff, and it is why one general assertion stands where a
first draft had three (`depends_on_healthy`, `env_equals`, `has_healthcheck`).
The two compose exercises that shipped name nothing a dotted key cannot reach.
The volume assertion was deferred too: no exercise in the first batch mounts
anything, and §13 holds this vocabulary to the exercises that exist.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Final

from practice.domain.checks.evaluation import CheckResult, matcher
from practice.domain.containers.evaluation import NO_DEFINITION, quote

if TYPE_CHECKING:
    from practice.domain.containers.evaluation import ContainerContext

__all__ = ["render", "service_value"]

#: What a report says about a key the service does not set.
_UNSET: Final = "<not set>"


def service_value(context: ContainerContext) -> CheckResult:
    """`service_value {service, key, pattern}` — a service setting matches.

    `key` is dotted (`environment.DATABASE_URL`, `depends_on.db.condition`,
    `healthcheck.test`), and a key the service does not set **fails** rather
    than erroring. That makes the negated form mean what it says:
    `{key: network_mode, pattern: '.', not: true}` passes exactly when nothing
    sets a network mode, and `network_mode: host` is the shortcut the
    database exercise rules out.
    """
    name = context.params.text("service")
    key = context.params.text("key")
    pattern = matcher(context.params)
    expected = f"{name}.{key} matches {pattern.pattern!r}"
    if context.query.error() is not None:
        return CheckResult(passed=False, expected=expected, actual=NO_DEFINITION)

    service = context.query.service(name)
    if service is None:
        declared = ", ".join(sorted(context.query.services())) or "none"
        return CheckResult(
            passed=False,
            expected=expected,
            actual=f"<no service {name!r}; declared: {declared}>",
        )

    value = _lookup(service, key.split("."))
    if value is None:
        return CheckResult(passed=False, expected=expected, actual=f"{key} is {_UNSET}")
    text = render(value)
    return CheckResult(
        passed=pattern.search(text) is not None,
        expected=expected,
        actual=f"{key} is {quote(text)!r}",
    )


def render(value: object) -> str:
    """A normalised compose value as one string a pattern can be written against.

    Lists join with spaces, so `test: ["CMD", "pg_isready", "-U", "app"]` reads
    as `CMD pg_isready -U app` and a pattern of `pg_isready` passes it either way.
    Booleans are YAML's spelling rather than Python's, because that is the
    spelling an author writes in a pattern.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Mapping):
        return " ".join(f"{key}={render(item)}" for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, str):
        return " ".join(render(item) for item in value)
    return str(value)


def _lookup(node: object, path: list[str]) -> object | None:
    for part in path:
        if not isinstance(node, Mapping) or part not in node:
            return None
        node = node[part]
    return node
