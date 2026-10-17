"""A compose file, read with PyYAML and normalised to compose's long form.

**Normalising is the grading decision, not a convenience.** Compose accepts
several spellings of the same setting:

    environment: [DATABASE_URL=postgres://db/app]
    environment: {DATABASE_URL: postgres://db/app}

    depends_on: [db]
    depends_on: {db: {condition: service_started}}

An assertion written against one spelling would fail a solver who used the
other, which is grading the text. So every service is rewritten into the long
form compose itself resolves to (`docker compose config` prints the same
shape) before an assertion sees it. The four settings rewritten are the four
the exercises read. Anything else passes through as YAML loaded it.

`healthcheck.test` as a bare string becomes `["CMD-SHELL", ...]`, which is
what compose does with it. A pattern of `pg_isready` matches both shapes,
because `render` joins a list with spaces.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

import yaml

__all__ = ["ComposeError", "parse_compose"]

_DEFAULT_CONDITION: Final = "service_started"


class ComposeError(Exception):
    """A compose file that compose would refuse, in a sentence the solver can act on."""


def parse_compose(text: str) -> dict[str, dict[str, object]]:
    """Every service, normalised. Raises `ComposeError`."""
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ComposeError(f"compose.yaml is not valid YAML: {exc}") from exc
    if not isinstance(document, Mapping):
        raise ComposeError("compose.yaml must be a mapping with a `services:` key")
    services = document.get("services")
    if not isinstance(services, Mapping) or not services:
        raise ComposeError("compose.yaml declares no `services:`")

    normalised: dict[str, dict[str, object]] = {}
    for name, body in services.items():
        if not isinstance(body, Mapping):
            raise ComposeError(f"service {name!r} must be a mapping of settings")
        normalised[str(name)] = _service(str(name), body)
    return normalised


def _service(name: str, body: Mapping[object, object]) -> dict[str, object]:
    service = {str(key): value for key, value in body.items()}
    if "environment" in service:
        service["environment"] = _environment(name, service["environment"])
    if "depends_on" in service:
        service["depends_on"] = _depends_on(name, service["depends_on"])
    if "ports" in service:
        service["ports"] = _ports(name, service["ports"])
    healthcheck = service.get("healthcheck")
    if isinstance(healthcheck, Mapping):
        check = {str(key): value for key, value in healthcheck.items()}
        if isinstance(check.get("test"), str):
            check["test"] = ["CMD-SHELL", check["test"]]
        service["healthcheck"] = check
    return service


def _environment(name: str, value: object) -> dict[str, str | None]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(key): _text(item) for key, item in value.items()}
    if isinstance(value, list):
        environment: dict[str, str | None] = {}
        for entry in value:
            key, equals, item = str(entry).partition("=")
            environment[key] = item if equals else None
        return environment
    raise ComposeError(f"service {name!r}: environment must be a list or a mapping")


def _depends_on(name: str, value: object) -> dict[str, dict[str, object]]:
    if isinstance(value, list):
        return {str(item): {"condition": _DEFAULT_CONDITION} for item in value}
    if isinstance(value, Mapping):
        dependencies: dict[str, dict[str, object]] = {}
        for other, settings in value.items():
            long = (
                {str(key): item for key, item in settings.items()}
                if isinstance(settings, Mapping)
                else {}
            )
            long.setdefault("condition", _DEFAULT_CONDITION)
            dependencies[str(other)] = long
        return dependencies
    raise ComposeError(f"service {name!r}: depends_on must be a list or a mapping")


def _ports(name: str, value: object) -> list[object]:
    if not isinstance(value, list):
        raise ComposeError(f"service {name!r}: ports must be a list")
    return [_port(entry) if isinstance(entry, str | int) else entry for entry in value]


def _port(entry: str | int) -> dict[str, object]:
    """`"127.0.0.1:8000:80/udp"` and its shorter forms, as compose's long form."""
    text, _, protocol = str(entry).partition("/")
    parts = text.rsplit(":", 2)
    target = parts.pop()
    published = parts.pop() if parts else None
    host_ip = parts.pop() if parts else None
    port: dict[str, object] = {"target": target, "protocol": protocol or "tcp"}
    if published:
        port["published"] = published
    if host_ip:
        port["host_ip"] = host_ip
    return port


def _text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
